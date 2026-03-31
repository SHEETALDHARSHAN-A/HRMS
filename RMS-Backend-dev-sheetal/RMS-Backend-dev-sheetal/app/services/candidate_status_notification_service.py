import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.resume_model import Profile
from app.db.models.job_post_model import JobDetails, RoundList
from app.utils.email_utils import send_candidate_status_email_async

logger = logging.getLogger(__name__)


class CandidateStatusNotificationService:
    """Send candidate status emails for shortlist/reject/under_review."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_status_email(
        self,
        *,
        profile_id: Any,
        round_id: Any,
        result: str,
        reason: str | None = None,
        source: str | None = None,
    ) -> Dict[str, Any]:
        profile = await self.db.get(Profile, profile_id)
        if not profile or not getattr(profile, "email", None):
            return {
                "sent": False,
                "reason": "missing_profile_or_email",
                "source": source,
            }

        round_row = await self.db.get(RoundList, round_id)
        if not round_row:
            return {
                "sent": False,
                "reason": "round_not_found",
                "source": source,
            }

        job_title = "Job Interview"
        if getattr(round_row, "job_id", None):
            job_title_row = await self.db.execute(
                select(JobDetails.job_title).where(JobDetails.id == round_row.job_id)
            )
            job_title = job_title_row.scalar_one_or_none() or job_title

        next_round_name = await self._fetch_next_round_name(round_row)

        try:
            sent = await send_candidate_status_email_async(
                to_email=profile.email,
                candidate_name=profile.name or "Candidate",
                job_title=job_title,
                round_name=round_row.round_name or "Interview",
                status=result,
                reason=reason,
                next_round_name=next_round_name,
                db=self.db,
            )
        except Exception as exc:
            logger.warning("Candidate status email failed: %s", exc)
            sent = False

        return {
            "sent": sent,
            "email": profile.email,
            "profile_id": str(profile.id),
            "round_id": str(round_row.id),
            "job_title": job_title,
            "round_name": round_row.round_name,
            "result": result,
            "source": source,
        }

    async def _fetch_next_round_name(self, round_row: RoundList) -> str | None:
        if not getattr(round_row, "job_id", None):
            return None
        if getattr(round_row, "round_order", None) is None:
            return None

        stmt = (
            select(RoundList.round_name)
            .where(RoundList.job_id == round_row.job_id)
            .where(RoundList.round_order == int(round_row.round_order) + 1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
