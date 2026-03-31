# app/services/shortlist_service/shortlist_service.py

import logging

from fastapi import HTTPException, status
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.update_shortlist_request import UpdateShortlistRequest
from app.db.repository.shortlist_repository import (
    get_job_round_overview,
    get_round_candidates,
    upsert_shortlist_result,
    update_interview_round_status
)
from app.services.scheduling_service.next_round_auto_scheduler import NextRoundAutoScheduler
from app.services.candidate_status_notification_service import CandidateStatusNotificationService

logger = logging.getLogger(__name__)

class ShortlistService:
    """Handles fetching and updating candidate shortlist results."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_job_round_overview(self) -> List[Dict[str, Any]]:
        try:
            return await get_job_round_overview(self.db_session)
        except Exception as e:
            logger.error(f"[ShortlistService] Error fetching job round overview: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to fetch job round overview."
            )

    async def get_candidates_by_job_and_round(
        self,
        job_id: str,
        round_id: str,
        result_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            candidates = await get_round_candidates(self.db_session, job_id, round_id, result_filter)
            return candidates
        except Exception as e:
            logger.error(f"[ShortlistService] Error fetching candidates for job {job_id}, round {round_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No such job post found or round not found in database."
            )

    async def update_candidate_status(
        self,
        profile_id: str,
        round_id: str,
        input: UpdateShortlistRequest
    ) -> Dict[str, Any]:
        new_result = input.new_result
        reason = input.reason
        valid_results = {"under_review", "shortlist", "reject"}

        if new_result not in valid_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid result '{new_result}'. Allowed: {', '.join(valid_results)}."
            )

        round_status_map = {
            "shortlist": "shortlisted",
            "under_review": "under_review",
            "reject": "rejected",
        }
        new_round_status = round_status_map.get(new_result, new_result)

        try:
            updated_entry = await upsert_shortlist_result(
                self.db_session,
                profile_id=profile_id,
                new_result=new_result,
                reason=reason or ""
            )

            success = await update_interview_round_status(
                self.db_session,
                profile_id=profile_id,
                round_id=round_id,
                new_status=new_round_status
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No such profile or round found in database."
                )

            auto_schedule_result = {
                "triggered": False,
                "reason": "not_shortlisted",
            }
            if new_round_status == "shortlisted":
                try:
                    auto_schedule_result = await NextRoundAutoScheduler(self.db_session).auto_schedule_next_round(
                        profile_id=profile_id,
                        current_round_id=round_id,
                        source="shortlist_update",
                    )
                    await self.db_session.commit()
                except Exception as auto_exc:
                    logger.warning(
                        "[ShortlistService] Auto-schedule failed for profile=%s round=%s: %s",
                        profile_id,
                        round_id,
                        auto_exc,
                    )
                    auto_schedule_result = {
                        "triggered": False,
                        "reason": "auto_schedule_failed",
                        "error": str(auto_exc),
                    }

            notification_result = {
                "sent": False,
                "reason": "not_attempted",
            }
            try:
                notification_result = await CandidateStatusNotificationService(self.db_session).send_status_email(
                    profile_id=profile_id,
                    round_id=round_id,
                    result=new_result,
                    reason=reason,
                    source="shortlist_update",
                )
            except Exception as notify_exc:
                logger.warning("[ShortlistService] Status email failed: %s", notify_exc)

            return {
                "shortlist_id": str(updated_entry.id),
                "profile_id": str(updated_entry.profile_id),
                "job_id": str(updated_entry.job_id),
                "new_result": updated_entry.result,
                "new_round_status": new_round_status,
                "reason": updated_entry.reason,
                "updated_at": updated_entry.updated_at.isoformat(),
                "auto_schedule": auto_schedule_result,
                "notification": notification_result,
            }

        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(ve)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[ShortlistService] Failed to update candidate status: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to update result. Please retry later."
            )
