import os
import logging
import time
import asyncio
import json
import re 
import urllib.error
import urllib.request
from typing import AsyncIterable, Optional, List, Tuple, Dict, Any
from uuid import uuid4
from sqlalchemy.future import select
from langfuse import get_client
from livekit import rtc
from livekit.agents import (
    Agent, AgentSession, ChatContext, JobContext, FunctionTool, ModelSettings,
    RoomInputOptions, RoomOutputOptions, WorkerOptions, UserStateChangedEvent,
    cli, stt, llm, Worker,
)
from livekit.protocol.models import ChatMessage
from livekit.agents.llm import ImageContent
from livekit.plugins import deepgram, groq, silero, elevenlabs
import config
from postgres_data_fetcher import (
    create_transcript_session, append_utterance_to_session,
    set_session_end_time, fetch_interview_context, get_db
)
from interview_logic import InterviewContextProcessor, CodingSessionAnalyzer 
from prompts import build_enhanced_interview_instructions
settings = config.settings

_langfuse = get_client(public_key=settings.LANGFUSE_PUBLIC_KEY)
logger = config.logger
print(f"LANGFUSE_PUBLIC_KEY: {settings.LANGFUSE_PUBLIC_KEY}")

class ProfessionalInterviewAgent(Agent):
    def __init__(self, instructions: str, room: rtc.Room, interview_context: Dict[str, Any]) -> None:
        super().__init__(
            instructions=instructions,
            llm=groq.LLM(model=settings.GROQ_MODEL, api_key=settings.ACTIVE_GROQ_API_KEY),
            stt=deepgram.STT(model="nova-2", api_key=settings.DEEPGRAM_API_KEY),
            tts=elevenlabs.TTS(api_key=settings.ELEVEN_LABS_API_KEY),
            vad=silero.VAD.load(
                min_speech_duration=0.1,
                min_silence_duration=1.0, 
                max_buffered_speech=60.0,
            ),
        )
        self.room = room
        self.session_id = str(uuid4()) # This ID will be the primary key for the transcript
        self.interview_context = interview_context
        
        # --- Context from PostgreSQL ---
        self.interview_duration = interview_context.get('interview_duration', 20)
        self.candidate_name = interview_context.get('candidate_name', 'candidate')
        
        # --- Store IDs for transcript logging ---
        self.db_job_id = interview_context.get('job_id')
        self.db_profile_id = interview_context.get('profile_id')
        self.db_round_id = interview_context.get('round_id')
        self.db_room_id = interview_context.get('room_id') # This is the interview_token
        self.candidate_email = interview_context.get('candidate_email')
        self.completion_reported = False
        
        self.interview_start_time: Optional[float] = None
        self.interview_end_time: Optional[float] = None

        # --- Simplified State ---
        self.warning_sent = False
        self.waiting_for_response = False
        self.silence_check_task: Optional[asyncio.Task] = None
        self.last_user_speech_time: Optional[float] = None
        self.is_user_speaking = False
        
        # Video/Screen Share State
        self.frames: List[Tuple[rtc.VideoFrame, float]] = []
        self.last_frame_time: float = 0.0
        self.video_stream: Optional[rtc.VideoStream] = None
        
        # --- Language selection is the ONLY state the agent tracks ---
        self.language_selection_phase = True
        self.preferred_language = "English" 
        self.current_system_instructions = instructions # The initial prompt

    async def close(self) -> None:
        if self.silence_check_task: self.silence_check_task.cancel()
        await self.close_video_stream()
        try: _langfuse.flush()
        except Exception: pass
        
    async def close_video_stream(self) -> None:
        if self.video_stream: await self.video_stream.aclose()
        self.video_stream = None
            
    async def check_for_silence(self): 
        await asyncio.sleep(60) # Reduced timeout to 60s
        if not self.waiting_for_response: return
        
        current_time = time.time()
        if (self.last_user_speech_time and (current_time - self.last_user_speech_time) < 30) or self.is_user_speaking:
            logger.info("User spoke recently or is speaking, extending wait time")
            self.silence_check_task = asyncio.create_task(self.check_for_silence())
            return
        
        if self.waiting_for_response:
            logger.warning("User has been silent for 60s. Prompting LLM for a gentle check.")
            self.waiting_for_response = False
            await self.session.generate_reply(instructions="The candidate has been silent for a minute. Gently check if they are still there or need help. Be patient and supportive.")

    def on_track_subscribed_wrapper(self, track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant) -> None:
        asyncio.create_task(self.on_track_subscribed(track, publication, participant))
        
    def _update_llm_instructions(self) -> None:
        """Dynamically rebuilds and updates the LLM instructions with the preferred language rule."""
        
        new_instructions = build_enhanced_interview_instructions(
            self.interview_context.get('job_data'),
            self.interview_context.get('candidate_profile_data', {}),
            self.interview_context.get('round_data'),
            preferred_language=self.preferred_language,
            project_context=self.interview_context.get('project_context', '')
        )
        self.current_system_instructions = new_instructions 
        logger.info(f"LLM instructions updated. Interview language set to: {self.preferred_language}")

    async def on_enter(self) -> None:
        self.interview_start_time = time.time()
        self.interview_end_time = self.interview_start_time + self.interview_duration * 60
        asyncio.create_task(self.enforce_interview_time())

        # --- Create transcript entry in PostgreSQL ---
        create_transcript_session(
            session_id=self.session_id,
            room_id=self.db_room_id,
            job_id=self.db_job_id,
            profile_id=self.db_profile_id,
            round_id=self.db_round_id
        )

        self.waiting_for_response = True
        
        self.session.on("user_state_changed", self.on_user_state_change)
        self.room.on("track_subscribed", self.on_track_subscribed_wrapper)

        await asyncio.sleep(5)
        if self.waiting_for_response: self.silence_check_task = asyncio.create_task(self.check_for_silence())
        
        # This is the *only* hardcoded agent speech.
        await self.session.generate_reply(instructions=f"""
            Start with a professional, welcoming greeting in English directed to the candidate: "Hello {self.candidate_name}, I'm Alex, an AI interviewer for the {self.interview_context.get('job_title', 'position')}. I'm excited to have you here today."
            
            Then immediately ask the candidate to confirm their preferred language for the interview: "We can continue in English, or with which language are you comfortable with to continue the interview? Please state your preferred language now."
            
            KEEP THIS INITIAL GREETING AND LANGUAGE QUESTION CONCISE. Then WAIT patiently for their response.
            DO NOT proceed with the rest of the introduction until they respond with their language preference.
            """)

    async def enforce_interview_time(self): 
        while time.time() < self.interview_end_time:
            if not self.warning_sent:
                remaining_seconds = self.interview_end_time - time.time()
                if remaining_seconds <= 300: # 5 minutes
                    # We just tell the LLM the time. It decides *how* to say it.
                    await self.session.generate_reply(instructions="INTERNAL_NOTE: Only 5 minutes remain. Politely inform the candidate, suggest wrapping up, and ask if they have final questions.")
                    self.warning_sent = True
            await asyncio.sleep(10)
        
        logger.info("Interview time elapsed. Forcing exit.")
        # Tell LLM to wrap up *now*.
        await self.session.generate_reply(instructions="INTERNAL_NOTE: The interview time is over. Please deliver your concluding remarks *now* and end the conversation.")
        await asyncio.sleep(10) # Give it time to speak
        await self.on_exit()
        
    async def on_exit(self) -> None: 
        if self.completion_reported:
            return
        self.completion_reported = True

        if self.silence_check_task: self.silence_check_task.cancel()
        set_session_end_time(self.session_id, time.time())
        await self._notify_backend_interview_complete()
        await self.close()

    def _build_interview_complete_url(self) -> str:
        base = (getattr(settings, "BACKEND_BASE_URL", "") or "").strip().rstrip("/")
        if not base:
            return ""

        lowered = base.lower()
        if lowered.endswith("/api/v1"):
            return f"{base}/interview/complete"
        if lowered.endswith("/api"):
            return f"{base}/v1/interview/complete"
        if lowered.endswith("/v1"):
            return f"{base}/interview/complete"
        return f"{base}/api/v1/interview/complete"

    async def _notify_backend_interview_complete(self) -> None:
        completion_url = self._build_interview_complete_url()
        internal_token = (getattr(settings, "INTERNAL_SERVICE_TOKEN", "") or "").strip()

        if not completion_url:
            logger.warning("Skipping interview completion callback: BACKEND_BASE_URL is not configured")
            return
        if not internal_token:
            logger.warning("Skipping interview completion callback: INTERNAL_SERVICE_TOKEN is not configured")
            return
        if not self.db_room_id or not self.candidate_email:
            logger.warning(
                "Skipping interview completion callback due to missing token/email. token_present=%s email_present=%s",
                bool(self.db_room_id),
                bool(self.candidate_email),
            )
            return

        payload = {
            "token": str(self.db_room_id),
            "email": str(self.candidate_email),
            "session_id": str(self.session_id),
            "final_notes": "Interview session ended by LiveKit interview agent.",
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-internal-token": internal_token,
        }

        def _post_completion() -> Tuple[int, str]:
            request = urllib.request.Request(
                completion_url,
                data=body,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                response_body = response.read().decode("utf-8", errors="ignore")
                return int(response.status), response_body

        try:
            status_code, response_body = await asyncio.to_thread(_post_completion)
            if 200 <= status_code < 300:
                logger.info(
                    "Interview completion callback succeeded for token %s (session %s). Response: %s",
                    self.db_room_id,
                    self.session_id,
                    response_body,
                )
            else:
                logger.warning(
                    "Interview completion callback returned non-success status %s for token %s. Response: %s",
                    status_code,
                    self.db_room_id,
                    response_body,
                )
        except urllib.error.HTTPError as exc:
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                error_body = ""
            logger.error(
                "Interview completion callback failed with HTTP %s for token %s. Response: %s",
                exc.code,
                self.db_room_id,
                error_body,
            )
        except Exception as exc:
            logger.error("Interview completion callback failed: %s", exc)

    def on_user_state_change(self, event: UserStateChangedEvent) -> None: pass
    
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None: 
        self.last_user_speech_time = time.time()
        self.is_user_speaking = False

        if self.silence_check_task:
            self.silence_check_task.cancel()
            self.silence_check_task = None

        self.waiting_for_response = False

        candidate_transcript = new_message.content
        if isinstance(candidate_transcript, list):
            candidate_transcript = " ".join(str(item) for item in candidate_transcript)

        # --- Log utterance to PostgreSQL ---
        utterance = {"timestamp": time.time(), "speaker": "candidate", "content": candidate_transcript}
        append_utterance_to_session(self.session_id, utterance)
        
        # --- This is the ONLY agent-side logic left ---
        if self.language_selection_phase:
            await self._handle_language_selection(candidate_transcript)
            return
        
        self.waiting_for_response = True
        self.silence_check_task = asyncio.create_task(self.check_for_silence())
        await self.session.generate_reply()
            
    async def _handle_language_selection(self, candidate_transcript: str) -> None:
        response_lower = candidate_transcript.lower()
        
        # Simple language detection
        preferred_language_map = {
            "tamil": "Tamil", "தமிழ்": "Tamil", "tamizh": "Tamil",
            "spanish": "Spanish", "español": "Spanish",
            "arabic": "Arabic", "العربية": "Arabic",
            "english": "English", "ingles": "English"
        }
        
        new_language = next((lang for key, lang in preferred_language_map.items() if key in response_lower), "English")
        
        self.language_selection_phase = False # This phase is over
        self.preferred_language = new_language
        self._update_llm_instructions() # Re-build the prompt with the new language

        llm_instructions = f"""
            INTERNAL_NOTE: The candidate has selected **{self.preferred_language}** as their language.
            Proceed *now* with your full introduction in {self.preferred_language}, as specified in your "Language & Introduction (Phase 1)" instructions.
            (Mention duration, screen sharing, and ask if they are ready).
            """
        
        self.waiting_for_response = True
        await asyncio.sleep(2)
        if self.waiting_for_response: self.silence_check_task = asyncio.create_task(self.check_for_silence())
        
        await self.session.generate_reply(instructions=llm_instructions)
            
    async def stt_node(self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings) -> Optional[AsyncIterable[stt.SpeechEvent]]: 
        try:
            async for event in super().stt_node(audio, model_settings):
                if event.type == stt.SpeechEventType.START_OF_SPEECH:
                    self.is_user_speaking = True
                    self.last_user_speech_time = time.time()
                elif event.type == stt.SpeechEventType.END_OF_SPEECH:
                    self.is_user_speaking = False
                elif event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
                    if event.alternatives[0].text.strip():
                        self.is_user_speaking = True
                        self.last_user_speech_time = time.time()
                elif event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                    self.last_user_speech_time = time.time()
                    self.is_user_speaking = False
                yield event
        except Exception as e:
            logger.error(f"STT error: {e}")
            raise

    async def llm_node(self, chat_ctx: llm.ChatContext, tools: List[FunctionTool], model_settings: ModelSettings) -> AsyncIterable[llm.ChatChunk]:
        copied_ctx = chat_ctx.copy()

        frames_to_use = self.current_frames()
        
        if frames_to_use:
            # Add screen share frames for analysis
            # This is great for the "Live Coding Session"
            image_content = ImageContent(image=frames_to_use[0][1], inference_detail="auto")
            copied_ctx.add_message(role="user", content=["[Current screen share view]", image_content])
        
        # Add the main system prompt
        copied_ctx.add_message(role="system", content=self.current_system_instructions)

        # Add a final dynamic instruction
        copied_ctx.add_message(
            role="system",
            content=f"""
            [CRITICAL: Respond in **{self.preferred_language}**]
            [Current time: {time.strftime('%H:%M')}. Interview started at: {time.strftime('%H:%M', time.localtime(self.interview_start_time))}]
            """
        )

        output = ""
        try:
            async for chunk in super().llm_node(copied_ctx, tools, model_settings):
                content = getattr(getattr(chunk, 'delta', chunk), 'content', '')
                if content:
                    output += content
                yield chunk

            if output:
                # --- Log bot utterance to PostgreSQL ---
                utterance = {"timestamp": time.time(), "speaker": "bot", "content": output}
                append_utterance_to_session(self.session_id, utterance)

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise
        
    def current_frames(self) -> List[Tuple[str, rtc.VideoFrame]]: 
        if not self.frames: return []
        current_time = time.time()
        # Get the most recent frame
        latest_frame, _ = max(self.frames, key=lambda ft: ft[1])
        return [("current", latest_frame)]

    async def on_track_subscribed(self, track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant) -> None:
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            logger.info("Video track subscribed, starting video stream processing")
            self.video_stream = rtc.VideoStream(track)
            asyncio.create_task(self.process_video_frames())

    async def process_video_frames(self) -> None:
        if not self.video_stream: return
        try:
            async for event in self.video_stream:
                if isinstance(event, rtc.VideoFrameEvent):
                    current_time = time.time()
                    # Throttle frame processing to once per second
                    if current_time - self.last_frame_time < 1.0: continue
                    self.last_frame_time = current_time
                    
                    frame = event.frame
                    self.frames.append((frame, current_time))
                    # Keep only frames from the last 30 seconds
                    cutoff_time = current_time - 30
                    self.frames = [(f, ts) for (f, ts) in self.frames if ts > cutoff_time]
        except Exception as e:
            logger.error(f"Error processing video frames: {e}")
        finally:
            await self.close_video_stream()


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    logger.info("Professional interview worker started")

    if not settings.ACTIVE_GROQ_API_KEY:
        logger.error("Groq API key is missing. Set GROQ_API_KEY (or legacy OPENAI_API_KEY with a Groq key).")
        return

    try:
        # Test the DB connection
        with get_db() as db:
            if db is None:
                 raise ConnectionError("Failed to get DB session from get_db()")
            db.execute(select(1))
        logger.info("Database connection test successful.")
    except Exception as e:
        logger.error(f"PostgreSQL DB not available. Agent is terminating. Error: {e}")
        return

    # --- The room_id IS the interview_token ---
    room_id = ctx.room.name
    if not room_id:
        logger.error("No room_id (interview_token) available - cannot proceed")
        return

    # --- Fetch context from PostgreSQL ---
    try:
        context_data = fetch_interview_context(room_id)
        
        if not context_data:
            logger.error(f"Failed to fetch essential context for room {room_id}. Terminating.")
            return

        job_data, profile_data, round_data, duration, candidate_name, db_ids = context_data
        
        job_id = db_ids.get('job_id')
        profile_id = db_ids.get('profile_id')
        round_id = db_ids.get('round_id')
        candidate_email = db_ids.get('candidate_email')
        
        if not job_id or not profile_id:
             logger.error(f"Missing job_id or profile_id for room {room_id}. Terminating.")
             return

    except Exception as e:
        logger.error(f"Critical error fetching context for room {room_id}: {e}")
        return

    # --- Process data using InterviewContextProcessor ---
    project_context = ""
    resume_content_summary = ""
    job_level = 'mid'
    required_skills = ['Programming', 'Problem Solving']

    if profile_data:
        # profile_data IS the extracted_content JSON
        required_skills, resume_content_summary, years_of_experience = InterviewContextProcessor.extract_relevant_context(profile_data)
        job_level = InterviewContextProcessor.determine_job_level(years_of_experience)

        if resume_content_summary:
            project_context = f"\nOverall Match Summary: {resume_content_summary}\n"
    # --------------------------------------------------------

    job_title = job_data.get('job_title', 'Software Engineer')

    # This context is passed to the agent and used to build the prompt
    interview_context = {
        'room_id': room_id, # This is the interview_token
        'job_title': job_title,
        'job_id': job_id,
        'profile_id': profile_id,
        'round_id': round_id,
        'candidate_email': candidate_email,
        'resume_content_summary': resume_content_summary,
        'job_data': job_data,
        'candidate_profile_data': profile_data, # The full extracted_content JSON
        'interview_duration': duration, # From PostgreSQL
        'job_level': job_level,
        'required_skills': required_skills, 
        'candidate_name': candidate_name or 'candidate',
        'project_context': project_context,
        'round_data': round_data, # Pass round data
    }
    
    try:
        # Build the initial prompt (will be rebuilt after language selection)
        instructions = build_enhanced_interview_instructions(
            job_data, 
            profile_data or {}, 
            round_data=round_data,
            project_context=project_context
            # Language defaults to English initially
        )
    except Exception as e:
        logger.error(f"Failed to build interview instructions: {e}")
        instructions = "You are a professional AI interviewer. Conduct a structured technical interview."

    agent = ProfessionalInterviewAgent(
        instructions=instructions,
        room=ctx.room,
        interview_context=interview_context
    )

    room_input = RoomInputOptions(video_enabled=True, audio_enabled=True, close_on_disconnect=True)
    room_output = RoomOutputOptions(audio_enabled=True, transcription_enabled=True)

    session = AgentSession()

    try:
        await session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=room_input,
            room_output_options=room_output,
        )
    except Exception as e:
        logger.error(f"Error during interview session: {e}")
        try:
            await agent.on_exit()
        except Exception as finalize_err:
            logger.error(f"Error during fallback interview finalization: {finalize_err}")

try:
    import livekit.agents.cli.watcher as _watcher
    from livekit.agents.utils.aio.duplex_unix import DuplexClosed
    _orig_read = getattr(_watcher, "_read_ipc_task", None)
    if _orig_read is not None:
        async def _safe_read_ipc_task(*args, **kwargs):
            try:
                await _orig_read(*args, **kwargs)
            except Exception as e:
                cause = getattr(e, "__cause__", None)
                if isinstance(e, DuplexClosed) or isinstance(cause, DuplexClosed):
                    return
                raise
        _watcher._read_ipc_task = _safe_read_ipc_task
except Exception:
    pass

# Main CLI runner
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )