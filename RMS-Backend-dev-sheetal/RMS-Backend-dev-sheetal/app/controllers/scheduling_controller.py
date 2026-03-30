# app/controllers/scheduling_controller.py

import logging

from typing import Dict, Any
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repository.scheduling_repository import get_scheduled_interviews
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest
from app.schemas.scheduling_interview_request import RescheduleInterviewRequest
from app.services.scheduling_service.scheduling_service import Scheduling
from app.utils.standard_response_utils import ResponseBuilder

logger = logging.getLogger(__name__)

async def scheduling_interview_controller(
    request: Request,
    interview_request: SchedulingInterviewRequest,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Handles the scheduling interview process by calling the Scheduling service.
    Returns a dictionary in the standard response format.
    """
    try:
        # Instantiate and run the service
        service = Scheduling(db=db)
        try:
            raw = await request.json()
            # Map frontend keys into the pydantic model if present
            if isinstance(raw, dict):
                if raw.get('custom_subject') and not getattr(interview_request, 'email_subject', None):
                    interview_request.email_subject = raw.get('custom_subject')
                if raw.get('custom_body') and not getattr(interview_request, 'email_body', None):
                    interview_request.email_body = raw.get('custom_body')
        except Exception:
            # If reading raw JSON fails for any reason, continue — the
            # interview_request may already contain the fields.
            logger.debug('Could not read raw request JSON to map custom template keys.')

        # The service returns a dictionary in the correct format
        result = await service.schedule_candidate(
            interview_request
        )

        return result

    except HTTPException as e:
        return ResponseBuilder.error(
            e.detail, 
            [e.detail], 
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in scheduling_interview_controller: {e}", exc_info=True)
        return ResponseBuilder.server_error(
            f"An unexpected error occurred during scheduling: {e}",
            # FIX: Remove status_code, as server_error uses HTTP_500_INTERNAL_SERVER_ERROR by default
            # status_code=status.HTTP_500_INTERNAL_SERVER_ERROR 
        )


async def get_scheduled_interviews_controller(
    job_id: str,
    round_id: str,
    db: AsyncSession
):
    """
    Fetches all scheduled interviews using the controller.
    Returns a dictionary in the standard response format.
    """
    try:
        result = await get_scheduled_interviews(job_id, round_id, db)
        
        return ResponseBuilder.success(
            "Scheduled interviews retrieved successfully.",
            {"interviews": result},
            status_code=status.HTTP_200_OK
        )

    except HTTPException as e:
        return ResponseBuilder.error(
            e.detail, 
            [e.detail], 
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_scheduled_interviews_controller: {e}", exc_info=True)
        return ResponseBuilder.server_error(
            f"An unexpected error occurred while fetching scheduled interviews: {e}",
            
        ) 


async def reschedule_interview_controller(
    request: Request,
    reschedule_request: RescheduleInterviewRequest,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Handles interview rescheduling requests."""
    try:
        service = Scheduling(db=db)
        try:
            raw = await request.json()
            if isinstance(raw, dict):
                if raw.get("custom_subject") and not getattr(reschedule_request, "email_subject", None):
                    reschedule_request.email_subject = raw.get("custom_subject")
                if raw.get("custom_body") and not getattr(reschedule_request, "email_body", None):
                    reschedule_request.email_body = raw.get("custom_body")
        except Exception:
            logger.debug("Could not read raw request JSON to map custom template keys for reschedule.")

        return await service.reschedule_candidate(reschedule_request)

    except HTTPException as e:
        return ResponseBuilder.error(
            e.detail,
            [e.detail],
            status_code=e.status_code,
        )
    except Exception as e:
        logger.error(f"Unexpected error in reschedule_interview_controller: {e}", exc_info=True)
        return ResponseBuilder.server_error(
            f"An unexpected error occurred during rescheduling: {e}",
        )