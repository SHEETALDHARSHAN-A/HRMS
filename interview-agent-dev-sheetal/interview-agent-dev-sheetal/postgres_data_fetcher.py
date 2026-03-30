import logging
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker, Session, joinedload, relationship
from sqlalchemy.future import select
from datetime import datetime, timezone
import uuid
import re

# Import settings and SessionLocal from our agent's config
try:
    # Prefer relative import when running as a package
    from .config import SessionLocal, logger
except Exception:
    # Fallback to absolute import when running the module as a script
    from config import SessionLocal, logger

# --- Agent-side SQLAlchemy Model Definitions ---
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, DateTime, Integer, Boolean, text

Base = declarative_base()

# --- ADD ALL MODELS THE AGENT NEEDS TO QUERY ---

class Scheduling(Base):
    __tablename__ = "scheduling_interviews" 
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey('profiles.id'), primary_key=True)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey('job_details.id'), primary_key=True)
    round_id = Column(PG_UUID(as_uuid=True), ForeignKey('interview_rounds.id'), primary_key=True)
    # Some deployments store the interview token as text in the DB. Use String here
    # to avoid type-mismatch errors when comparing incoming token strings.
    interview_token = Column(String, unique=True, nullable=False, index=True)
    scheduled_datetime = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="scheduled")
    interview_duration = Column(Integer, nullable=False, default=20)
    
    # Relationships
    profile = relationship("Profile")
    job = relationship("JobDetails")
    interview_round = relationship("InterviewRounds")

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    extracted_content = Column(JSONB, nullable=False)

class JobDetails(Base):
    __tablename__ = "job_details"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_title = Column(String, nullable=False)
    # Add fields that might be useful for the prompt
    minimum_experience = Column(Integer)
    maximum_experience = Column(Integer)
    
class InterviewRounds(Base):
    __tablename__ = "interview_rounds"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"), nullable=False)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    # This 'round_id' points to 'round_list.id'
    round_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id"), nullable=False)
    status = Column(String, nullable=True)
    
    # Relationship
    round_details = relationship("RoundList")

class RoundList(Base):
    __tablename__ = "round_list"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"))
    round_name = Column(String, nullable=False)
    round_description = Column(Text)

class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey('profiles.id'), nullable=False)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey('job_details.id'), nullable=False)
    # This should be the 'interview_rounds.id' (the specific instance)
    round_id = Column(PG_UUID(as_uuid=True), ForeignKey('interview_rounds.id'), nullable=True)
    room_id = Column(String, index=True)
    conversation = Column(JSONB, nullable=False, default=list)
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime(timezone=True), nullable=True)

# --- ADD THE NEW AGENT CONFIG MODEL ---
class AgentRoundConfig(Base):
    __tablename__ = "round_config"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"), nullable=False, index=True)
    round_list_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id"), nullable=True, index=True)
    round_name = Column(String, nullable=False, default="Configured Round")
    round_focus = Column(Text)
    persona = Column(String, default='alex')
    key_skills = Column(JSONB, default=list)
    custom_questions = Column(JSONB, default=list)
    forbidden_topics = Column(JSONB, default=list)
    coding_enabled = Column(Boolean, default=False, nullable=False)
    coding_question_mode = Column(String, default='ai', nullable=False)
    coding_difficulty = Column(String, default='medium')
    coding_languages = Column(JSONB, default=list)
    provided_coding_question = Column(Text)

# --- End of Model Definitions ---


@contextmanager
def get_db() -> Session:
    """Provides a transactional scope around a series of operations."""
    if SessionLocal is None:
        logger.error("Database SessionLocal is not initialized.")
        raise ConnectionError("Database not configured.")
        
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def fetch_interview_context(room_name: str) -> Optional[Tuple[Dict, Dict, Dict, int, str, Dict]]:
    """
    Fetches all interview context from PostgreSQL using the room_name (which is the interview_token).
    
    Returns: (job_data, profile_data, round_data, duration, candidate_name, db_ids)
    - job_data: Basic info about the job.
    - profile_data: The candidate's extracted_content JSON.
    - round_data: The *specific agent configuration* for this round.
    - duration: Interview duration in minutes.
    - candidate_name: Candidate's name.
    - db_ids: Internal UUIDs and candidate email for transcript logging/callbacks.
    """
    with get_db() as db:
        try:
            try:
                interview_token_value = str(uuid.UUID(room_name))
            except Exception:
                interview_token_value = str(room_name)
            
            # --- 1. Fetch Schedule and related data ---
            query = (
                select(Scheduling)
                .where(Scheduling.interview_token == interview_token_value)
                .options(
                    joinedload(Scheduling.profile),
                    joinedload(Scheduling.job),
                    joinedload(Scheduling.interview_round).joinedload(InterviewRounds.round_details)
                )
            )
            
            schedule = db.execute(query).scalars().one_or_none()

            
            if not schedule:
                logger.error(f"No schedule found for interview_token (room_name): {room_name}")
                return None

            profile = schedule.profile
            job = schedule.job
            # In some deployments scheduling.round_id stores interview_rounds.id,
            # while in others it stores round_list.id. Resolve both safely.
            interview_round = schedule.interview_round
            
            if not profile or not job:
                logger.error(f"Missing Profile or Job for schedule: {room_name}")
                return None

            # --- 2. Prepare basic data ---
            job_data = {
                "id": str(job.id),
                "job_title": job.job_title,
                "minimum_experience": job.minimum_experience,
                "maximum_experience": job.maximum_experience,
            }
            
            profile_data = profile.extracted_content
            duration = getattr(schedule, 'interview_duration', 20) or 20
            candidate_name = profile.name or "Candidate"

            # --- 3. Resolve round details and fetch specific agent configuration ---
            round_data = None
            db_round_list_id = None
            round_details = interview_round.round_details if interview_round and interview_round.round_details else None

            if not interview_round and schedule.round_id:
                round_from_instance = (
                    db.query(InterviewRounds)
                    .options(joinedload(InterviewRounds.round_details))
                    .filter(
                        InterviewRounds.job_id == schedule.job_id,
                        InterviewRounds.profile_id == schedule.profile_id,
                        InterviewRounds.round_id == schedule.round_id,
                    )
                    .order_by(InterviewRounds.id.desc())
                    .one_or_none()
                )
                if round_from_instance:
                    interview_round = round_from_instance
                    round_details = round_from_instance.round_details

            if not round_details and schedule.round_id:
                round_details = (
                    db.query(RoundList)
                    .filter(RoundList.id == schedule.round_id)
                    .one_or_none()
                )

            if round_details:
                db_round_list_id = round_details.id

                config_query = (
                    select(AgentRoundConfig)
                    .where(
                        AgentRoundConfig.job_id == job.id,
                        AgentRoundConfig.round_list_id == db_round_list_id,
                    )
                )
                agent_config = db.execute(config_query).scalars().one_or_none()

                if agent_config:
                    logger.info(f"Loaded agent config '{agent_config.id}' for job {job.id}, round {db_round_list_id}")
                    round_data = {
                        "id": str(agent_config.id),
                        "round_name": agent_config.round_name,
                        "round_focus": agent_config.round_focus,
                        "persona": agent_config.persona,
                        "key_skills": agent_config.key_skills or [],
                        "custom_questions": agent_config.custom_questions or [],
                        "forbidden_topics": agent_config.forbidden_topics or [],
                        "coding_enabled": bool(getattr(agent_config, "coding_enabled", False)),
                        "coding_question_mode": getattr(agent_config, "coding_question_mode", "ai") or "ai",
                        "coding_difficulty": getattr(agent_config, "coding_difficulty", "medium") or "medium",
                        "coding_languages": getattr(agent_config, "coding_languages", None) or ["python"],
                        "provided_coding_question": getattr(agent_config, "provided_coding_question", None),
                    }
                else:
                    logger.warning(
                        f"No AgentRoundConfig found for job {job.id}, round {db_round_list_id}. Using default round description."
                    )
                    round_data = {
                        "round_name": round_details.round_name,
                        "round_description": round_details.round_description,
                    }
            
            if not round_data:
                 logger.warning(f"No round data or interview_round link found for room {room_name}. Using generic defaults.")
                 round_data = {
                     "round_name": "Technical Interview",
                     "round_description": "Assess general technical skills."
                 }
            # --- END OF NEW LOGIC ---
            
            db_ids = {
                "job_id": str(job.id),
                "profile_id": str(profile.id),
                "round_id": str(interview_round.id) if interview_round else None,
                "round_list_id": str(db_round_list_id) if db_round_list_id else None,
                "candidate_email": profile.email,
            }
            
            logger.info(f"Successfully fetched context for room {room_name}.")
            
            return job_data, profile_data, round_data, duration, candidate_name, db_ids

        except Exception as e:
            logger.error(f"Error fetching interview context: {e}", exc_info=True)
            return None

def create_transcript_session(
    session_id: str, 
    room_id: str, 
    job_id: Any, 
    profile_id: Any, 
    round_id: Any
) -> bool:
    """Creates a new transcript document."""
    with get_db() as db:
        try:
            existing = db.query(Transcript).filter(Transcript.id == uuid.UUID(session_id)).one_or_none()
            if existing:
                logger.warning(f"Transcript session {session_id} already exists.")
                return True

            resolved_round_id = None
            if round_id:
                round_uuid = None
                try:
                    round_uuid = uuid.UUID(str(round_id))
                except Exception:
                    round_uuid = None

                if round_uuid:
                    existing_round = db.query(InterviewRounds).filter(InterviewRounds.id == round_uuid).one_or_none()
                    resolved_round_id = round_uuid if existing_round else None
                if not resolved_round_id:
                    logger.warning(
                        "Transcript round_id %s does not map to interview_rounds.id; saving transcript with null round_id",
                        round_id,
                    )
                
            new_transcript = Transcript(
                id=uuid.UUID(session_id),
                room_id=room_id,
                job_id=job_id,
                profile_id=profile_id,
                round_id=resolved_round_id,
                conversation=[],
                start_time=datetime.now(timezone.utc)
            )
            db.add(new_transcript)
            db.commit()
            logger.info(f"Created new transcript session: {session_id}")
            return True
        except Exception as e:
            msg = str(e).lower()
            if 'transcripts' in msg or 'undefinedtable' in msg or 'relation "transcripts"' in msg:
                logger.error(
                    "Error creating transcript session: `transcripts` table does not exist. "
                    "Apply the migration at `RMS-Backend-dev-sheetal/RMS-Backend-dev-sheetal/scripts/migrations/004_create_transcripts.sql` or create the table in your DB."
                )
                return False
            logger.error(f"Error creating transcript session: {e}")
            return False

def append_utterance_to_session(session_id: str, utterance: Dict[str, Any]) -> None:
    """Appends a new utterance to the conversation JSONB array."""
    with get_db() as db:
        try:
            transcript = db.query(Transcript).filter(Transcript.id == uuid.UUID(session_id)).one_or_none()
            if not transcript:
                logger.error(f"Cannot append utterance: Transcript session {session_id} not found.")
                return

            new_conversation = (transcript.conversation or []) + [utterance]
            
            transcript.conversation = new_conversation
            db.commit()
            
        except Exception as e:
            logger.error(f"Error appending utterance: {e}. Session ID: {session_id}")

def set_session_end_time(session_id: str, end_time: float) -> None:
    """Sets the end time for a given transcript session."""
    with get_db() as db:
        try:
            transcript = db.query(Transcript).filter(Transcript.id == uuid.UUID(session_id)).one_or_none()
            if transcript:
                transcript.end_time = datetime.fromtimestamp(end_time, tz=timezone.utc)
                db.commit()
        except Exception as e:
            msg = str(e).lower()
            if 'transcripts' in msg or 'undefinedtable' in msg or 'relation "transcripts"' in msg:
                logger.error(
                    "Error setting end time: `transcripts` table does not exist. "
                    "Apply the migration at `RMS-Backend-dev-sheetal/RMS-Backend-dev-sheetal/scripts/migrations/004_create_transcripts.sql` or create the table in your DB."
                )
                return
            logger.error(f"Error setting end time: {e}")