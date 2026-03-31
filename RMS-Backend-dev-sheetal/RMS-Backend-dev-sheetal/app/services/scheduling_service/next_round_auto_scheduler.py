import json
import logging
import uuid
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.db.models.agent_config_model import AgentRoundConfig
from app.db.models.job_post_model import JobDetails, RoundList
from app.db.models.resume_model import InterviewRounds, Profile
from app.db.models.scheduling_model import Scheduling
from app.db.redis_manager import RedisManager
from app.utils.email_utils import send_interview_invite_email_async

logger = logging.getLogger(__name__)
settings = AppConfig()


def _to_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except Exception:
        return None


class NextRoundAutoScheduler:
    """Creates mode-aware next-round schedules when a candidate is advanced."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_schedule_next_round(
        self,
        *,
        profile_id: Any,
        current_round_id: Any,
        source: str = "status_update",
    ) -> Dict[str, Any]:
        profile_uuid = _to_uuid(profile_id)
        current_round_uuid = _to_uuid(current_round_id)
        if profile_uuid is None or current_round_uuid is None:
            return {
                "triggered": False,
                "reason": "invalid_ids",
            }

        current_interview_round, current_round = await self._resolve_current_round(
            profile_uuid=profile_uuid,
            current_round_uuid=current_round_uuid,
        )
        if current_round is None:
            return {
                "triggered": False,
                "reason": "current_round_not_found",
            }

        job_uuid = _to_uuid(getattr(current_round, "job_id", None))
        if job_uuid is None:
            return {
                "triggered": False,
                "reason": "missing_job_context",
            }

        if current_round.round_order is None:
            return {
                "triggered": False,
                "reason": "missing_round_order",
            }

        next_round_stmt = (
            select(RoundList)
            .where(RoundList.job_id == job_uuid)
            .where(RoundList.round_order == int(current_round.round_order) + 1)
        )
        next_round = (await self.db.execute(next_round_stmt)).scalar_one_or_none()
        if next_round is None:
            return {
                "triggered": False,
                "reason": "no_next_round",
                "is_final_round": True,
            }

        next_interview_round = await self._ensure_next_interview_round(
            job_id=job_uuid,
            profile_id=profile_uuid,
            round_list_id=next_round.id,
        )

        config = await self._fetch_round_config(job_id=job_uuid, round_list_id=next_round.id)
        round_mode = self._resolve_round_mode(config)
        interview_type = self._interview_type_from_mode(round_mode)

        scheduled_datetime = await self._pick_schedule_time(
            profile_id=profile_uuid,
            job_id=job_uuid,
            current_interview_round_id=getattr(current_interview_round, "id", None),
        )

        duration_minutes = self._duration_minutes(config)
        assessment_end = None
        if round_mode in {"coding_assessment", "apti_assessment"}:
            assessment_end = scheduled_datetime + timedelta(minutes=duration_minutes)

        profile = await self._fetch_profile(profile_uuid)

        existing_schedule = await self._fetch_schedule(
            profile_id=profile_uuid,
            job_id=job_uuid,
            interview_round_id=next_interview_round.id,
        )

        if existing_schedule is None:
            interview_token = uuid.uuid4()
            schedule = Scheduling(
                profile_id=profile_uuid,
                job_id=job_uuid,
                round_id=next_interview_round.id,
                interview_token=interview_token,
                interviewer_id=getattr(config, "interviewer_id", None),
                scheduled_datetime=scheduled_datetime,
                interview_duration=duration_minutes,
                status="scheduled",
                email_sent=False,
                phone_number=getattr(profile, "phone_number", None) if profile else None,
                interview_type=interview_type,
                level_of_interview=self._level_of_interview(config),
                expired_at=assessment_end,
            )
            self.db.add(schedule)
        else:
            interview_token = existing_schedule.interview_token
            existing_schedule.scheduled_datetime = scheduled_datetime
            existing_schedule.status = "scheduled"
            existing_schedule.interview_type = interview_type
            existing_schedule.level_of_interview = self._level_of_interview(config)
            existing_schedule.interviewer_id = getattr(config, "interviewer_id", None)
            existing_schedule.expired_at = assessment_end
            existing_schedule.interview_duration = duration_minutes
            existing_schedule.rescheduled_count = int(existing_schedule.rescheduled_count or 0) + 1
            if profile and not existing_schedule.phone_number:
                existing_schedule.phone_number = getattr(profile, "phone_number", None)

        next_interview_round.status = (
            "assessment_scheduled" if round_mode in {"coding_assessment", "apti_assessment"} else "interview_scheduled"
        )

        next_next_round_name = await self._fetch_next_round_name(job_uuid=job_uuid, next_round_order=int(next_round.round_order) + 1)
        job_title = await self._fetch_job_title(job_uuid)

        email_sent = False
        profile_email = getattr(profile, "email", None) if profile else None
        if profile_email:
            candidate_name = (getattr(profile, "name", None) or "Candidate").strip() or "Candidate"
            email_subject, email_body = self._email_template_for_mode(
                mode=round_mode,
                candidate_name=candidate_name,
                round_name=str(next_round.round_name or "Interview Round"),
                start_at=scheduled_datetime,
                end_at=assessment_end,
                secure_required=(round_mode in {"coding_assessment", "apti_assessment"}),
            )
            base_url = str(getattr(settings, "frontend_url", "") or "").rstrip("/")
            interview_link = self._build_interview_link(
                base_url=base_url,
                interview_token=str(interview_token),
                candidate_email=profile_email,
                round_mode=round_mode,
            )
            try:
                email_sent = await send_interview_invite_email_async(
                    to_email=profile_email,
                    candidate_name=candidate_name,
                    interview_link=interview_link,
                    interview_token=str(interview_token),
                    interview_datetime=scheduled_datetime,
                    job_title=job_title or "Job Interview",
                    round_name=str(next_round.round_name or "Interview Round"),
                    next_round_name=next_next_round_name or "Final Review",
                    custom_subject=email_subject,
                    custom_body=email_body,
                    db=self.db,
                )
            except Exception as email_exc:
                logger.warning("Auto-schedule email failed for profile=%s round=%s: %s", profile_uuid, next_round.id, email_exc)
                email_sent = False

        try:
            await self._store_runtime_policy(
                interview_token=str(interview_token),
                mode=round_mode,
                start_at=scheduled_datetime,
                end_at=assessment_end,
            )
        except Exception as policy_exc:
            logger.warning("Failed to store runtime policy for token=%s: %s", interview_token, policy_exc)

        return {
            "triggered": True,
            "source": source,
            "job_id": str(job_uuid),
            "profile_id": str(profile_uuid),
            "current_round_id": str(current_round.id),
            "next_round_id": str(next_round.id),
            "next_round_name": next_round.round_name,
            "next_round_order": next_round.round_order,
            "next_round_mode": round_mode,
            "interview_round_id": str(next_interview_round.id),
            "interview_token": str(interview_token),
            "scheduled_datetime": scheduled_datetime.isoformat(),
            "assessment_end_datetime": assessment_end.isoformat() if assessment_end else None,
            "interview_type": interview_type,
            "email_sent": email_sent,
        }

    async def _resolve_current_round(
        self,
        *,
        profile_uuid: uuid.UUID,
        current_round_uuid: uuid.UUID,
    ) -> tuple[Optional[InterviewRounds], Optional[RoundList]]:
        interview_round_stmt = (
            select(InterviewRounds)
            .where(InterviewRounds.profile_id == profile_uuid)
            .where(InterviewRounds.round_id == current_round_uuid)
            .order_by(InterviewRounds.id.desc())
        )
        interview_round = (await self.db.execute(interview_round_stmt)).scalars().first()

        round_stmt = select(RoundList).where(RoundList.id == current_round_uuid)
        round_row = (await self.db.execute(round_stmt)).scalar_one_or_none()

        if round_row is None and interview_round is not None:
            round_stmt = select(RoundList).where(RoundList.id == interview_round.round_id)
            round_row = (await self.db.execute(round_stmt)).scalar_one_or_none()

        if interview_round is None and round_row is not None:
            by_round_stmt = (
                select(InterviewRounds)
                .where(InterviewRounds.profile_id == profile_uuid)
                .where(InterviewRounds.round_id == round_row.id)
                .order_by(InterviewRounds.id.desc())
            )
            interview_round = (await self.db.execute(by_round_stmt)).scalars().first()

        return interview_round, round_row

    async def _ensure_next_interview_round(
        self,
        *,
        job_id: uuid.UUID,
        profile_id: uuid.UUID,
        round_list_id: uuid.UUID,
    ) -> InterviewRounds:
        stmt = (
            select(InterviewRounds)
            .where(InterviewRounds.job_id == job_id)
            .where(InterviewRounds.profile_id == profile_id)
            .where(InterviewRounds.round_id == round_list_id)
            .order_by(InterviewRounds.id.desc())
        )
        instance = (await self.db.execute(stmt)).scalars().first()
        if instance is not None:
            return instance

        instance = InterviewRounds(
            job_id=job_id,
            profile_id=profile_id,
            round_id=round_list_id,
            status="under_review",
        )
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def _fetch_round_config(self, *, job_id: uuid.UUID, round_list_id: uuid.UUID) -> Optional[AgentRoundConfig]:
        stmt = (
            select(AgentRoundConfig)
            .where(AgentRoundConfig.job_id == job_id)
            .where(AgentRoundConfig.round_list_id == round_list_id)
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _fetch_schedule(
        self,
        *,
        profile_id: uuid.UUID,
        job_id: uuid.UUID,
        interview_round_id: uuid.UUID,
    ) -> Optional[Scheduling]:
        stmt = (
            select(Scheduling)
            .where(Scheduling.profile_id == profile_id)
            .where(Scheduling.job_id == job_id)
            .where(Scheduling.round_id == interview_round_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _fetch_profile(self, profile_id: uuid.UUID) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.id == profile_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _fetch_job_title(self, job_id: uuid.UUID) -> Optional[str]:
        stmt = select(JobDetails.job_title).where(JobDetails.id == job_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _fetch_next_round_name(self, *, job_uuid: uuid.UUID, next_round_order: int) -> Optional[str]:
        stmt = (
            select(RoundList.round_name)
            .where(RoundList.job_id == job_uuid)
            .where(RoundList.round_order == next_round_order)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _pick_schedule_time(
        self,
        *,
        profile_id: uuid.UUID,
        job_id: uuid.UUID,
        current_interview_round_id: Any,
    ) -> datetime:
        now_utc = datetime.now(timezone.utc)

        stmt = (
            select(Scheduling)
            .where(Scheduling.profile_id == profile_id)
            .where(Scheduling.job_id == job_id)
            .order_by(Scheduling.scheduled_datetime.desc())
        )
        previous_schedule = (await self.db.execute(stmt)).scalars().first()

        if previous_schedule and previous_schedule.scheduled_datetime:
            candidate = previous_schedule.scheduled_datetime
            if candidate.tzinfo is None:
                candidate = candidate.replace(tzinfo=timezone.utc)
            candidate = candidate + timedelta(days=1)
        else:
            candidate = now_utc + timedelta(hours=24)

        min_allowed = now_utc + timedelta(minutes=15)
        if candidate < min_allowed:
            candidate = min_allowed

        return candidate.replace(second=0, microsecond=0)

    @staticmethod
    def _resolve_round_mode(config: Optional[AgentRoundConfig]) -> str:
        if config is None:
            return "agent_live"

        mode = str(getattr(config, "interview_mode", "") or "").strip().lower()
        coding_enabled = bool(getattr(config, "coding_enabled", False))
        mcq_enabled = bool(getattr(config, "mcq_enabled", False))

        if mode in {"offline", "in_person", "in-person", "inperson", "person"}:
            return "in_person"
        if mode in {"apti", "aptitude", "mcq", "quiz", "apti_screening"}:
            return "apti_assessment"
        if mode in {"coding", "code", "coding_challenge"}:
            return "coding_assessment"
        if coding_enabled:
            return "coding_assessment"
        if mcq_enabled:
            return "apti_assessment"
        return "agent_live"

    @staticmethod
    def _interview_type_from_mode(mode: str) -> str:
        mapping = {
            "agent_live": "Agent_interview",
            "coding_assessment": "Coding_assessment",
            "apti_assessment": "Aptitude_assessment",
            "in_person": "In_person_interview",
        }
        return mapping.get(mode, "Agent_interview")

    @staticmethod
    def _duration_minutes(config: Optional[AgentRoundConfig]) -> int:
        if config is None:
            return 60

        for attr in ("interview_time_max", "interview_time_min"):
            raw = getattr(config, attr, None)
            if raw is None:
                continue
            try:
                val = int(raw)
            except Exception:
                continue
            if val > 0:
                return min(240, max(30, val))
        return 60

    @staticmethod
    def _level_of_interview(config: Optional[AgentRoundConfig]) -> str:
        if config is None:
            return "medium"
        if getattr(config, "coding_enabled", False):
            return str(getattr(config, "coding_difficulty", None) or "medium")
        if getattr(config, "mcq_enabled", False):
            return str(getattr(config, "mcq_difficulty", None) or "medium")
        return "medium"

    @staticmethod
    def _email_template_for_mode(
        *,
        mode: str,
        candidate_name: str,
        round_name: str,
        start_at: datetime,
        end_at: Optional[datetime],
        secure_required: bool,
    ) -> tuple[str, str]:
        start_text = start_at.astimezone(timezone.utc).strftime("%d-%m-%Y %H:%M UTC")
        end_text = end_at.astimezone(timezone.utc).strftime("%d-%m-%Y %H:%M UTC") if end_at else ""

        if mode == "coding_assessment":
            subject = f"Coding Round Scheduled - {round_name}"
            body = (
                f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #1f2937;">
                    <div style="max-width: 640px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 10px;">
                        <h2 style="margin: 0 0 12px; color: #0f172a;">Coding Round Scheduled</h2>
                        <p>Hi <strong>{candidate_name}</strong>,</p>
                        <p>Your coding round (<strong>{round_name}</strong>) has been scheduled automatically.</p>
                        <p><strong>Start:</strong> {start_text}<br><strong>End:</strong> {end_text}</p>
                        <p><strong>Security requirements:</strong></p>
                        <ul>
                            <li>Secure browser mode must be enabled</li>
                            <li>Camera and proctoring checks (head/eye movement) must stay active</li>
                        </ul>
                        <p>Use the assessment link below within the allowed window:</p>
                        <p><a href="{{JOIN_URL}}">Open Assessment</a></p>
                        <p><strong>Room ID:</strong> {{ROOM_CODE}}</p>
                        <p style="margin-top: 24px;">Regards,<br><strong>RMS Team</strong></p>
                    </div>
                </body>
                </html>
                """
            )
            return subject, body

        if mode == "apti_assessment":
            subject = f"Aptitude Round Scheduled - {round_name}"
            body = (
                f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #1f2937;">
                    <div style="max-width: 640px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 10px;">
                        <h2 style="margin: 0 0 12px; color: #0f172a;">Aptitude Round Scheduled</h2>
                        <p>Hi <strong>{candidate_name}</strong>,</p>
                        <p>Your aptitude round (<strong>{round_name}</strong>) has been scheduled automatically.</p>
                        <p><strong>Start:</strong> {start_text}<br><strong>End:</strong> {end_text}</p>
                        <p><strong>Security requirements:</strong></p>
                        <ul>
                            <li>Secure browser mode must be enabled</li>
                            <li>Camera and proctoring checks (head/eye movement) must stay active</li>
                        </ul>
                        <p>Use the assessment link below within the allowed window:</p>
                        <p><a href="{{JOIN_URL}}">Open Assessment</a></p>
                        <p><strong>Room ID:</strong> {{ROOM_CODE}}</p>
                        <p style="margin-top: 24px;">Regards,<br><strong>RMS Team</strong></p>
                    </div>
                </body>
                </html>
                """
            )
            return subject, body

        if mode == "in_person":
            subject = f"In-person Interview Scheduled - {round_name}"
            body = (
                f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #1f2937;">
                    <div style="max-width: 640px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 10px;">
                        <h2 style="margin: 0 0 12px; color: #0f172a;">In-person Interview Scheduled</h2>
                        <p>Hi <strong>{candidate_name}</strong>,</p>
                        <p>Your in-person interview round (<strong>{round_name}</strong>) has been scheduled automatically.</p>
                        <p><strong>Meeting time:</strong> {start_text}</p>
                        <p>Meeting room and interviewer details will be available on your schedule panel.</p>
                        <p>If needed, this slot can be rescheduled by your recruiter.</p>
                        <p style="margin-top: 24px;">Regards,<br><strong>RMS Team</strong></p>
                    </div>
                </body>
                </html>
                """
            )
            return subject, body

        subject = f"Agent Live Interview Scheduled - {round_name}"
        body = (
            f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #1f2937;">
                <div style="max-width: 640px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 10px;">
                    <h2 style="margin: 0 0 12px; color: #0f172a;">Agent Live Interview Scheduled</h2>
                    <p>Hi <strong>{candidate_name}</strong>,</p>
                    <p>You have moved to the next agent live interview round (<strong>{round_name}</strong>).</p>
                    <p><strong>Meeting time:</strong> {start_text}</p>
                    <p>The live interview room will be activated shortly before the start time.</p>
                    <p><a href="{{JOIN_URL}}">Join Interview</a></p>
                    <p><strong>Room ID:</strong> {{ROOM_CODE}}</p>
                    <p style="margin-top: 24px;">Regards,<br><strong>RMS Team</strong></p>
                </div>
            </body>
            </html>
            """
        )
        return subject, body

    async def _store_runtime_policy(
        self,
        *,
        interview_token: str,
        mode: str,
        start_at: datetime,
        end_at: Optional[datetime],
    ) -> None:
        policy = {
            "mode": mode,
            "startAt": start_at.isoformat(),
            "endAt": end_at.isoformat() if end_at else None,
            "enforceSecurity": False,
            "secureBrowserRequired": False,
            "proctoringRequired": False,
            "headMovementCheck": False,
            "eyeFocusCheck": False,
            "livekitReadyBeforeMinutes": 5 if mode == "agent_live" else 0,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        redis = RedisManager.get_client()
        await redis.set(
            f"interview_runtime_policy:{interview_token}",
            json.dumps(policy, ensure_ascii=True),
            ex=60 * 60 * 24 * 7,
        )

    @staticmethod
    def _build_interview_link(
        *,
        base_url: str,
        interview_token: str,
        candidate_email: str | None,
        round_mode: str,
    ) -> str:
        base = (base_url or "").rstrip("/")
        if round_mode in {"coding_assessment", "apti_assessment"}:
            email_param = f"&email={quote(candidate_email)}" if candidate_email else ""
            path = f"/interview/coding?token={interview_token}{email_param}"
        else:
            path = f"/interview/join?token={interview_token}"
        return f"{base}{path}" if base else path
