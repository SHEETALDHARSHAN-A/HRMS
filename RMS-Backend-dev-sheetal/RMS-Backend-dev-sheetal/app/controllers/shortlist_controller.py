# app/controllers/shortlist_controller.py

import logging
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.standard_response import StandardResponse
from app.utils.standard_response_utils import ResponseBuilder
from app.schemas.update_shortlist_request import UpdateShortlistRequest
from app.services.shortlist_service.shortlist_service import ShortlistService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _validate_uuid(id_value: str, id_name: str):
    """Helper to validate UUID format."""
    try:
        uuid.UUID(str(id_value))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a valid {id_name} UUID"
        )


async def get_job_round_overview_controller(
    db: AsyncSession
) -> StandardResponse:
    try:
        service = ShortlistService(db_session=db)
        overview_data = await service.get_job_round_overview()

        return ResponseBuilder.success(
            message="Fetched job round overview.",
            data={"job_round_overview": overview_data},
            status_code=status.HTTP_200_OK
        )
    except HTTPException as e:
        return ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code)
    except Exception as e:
        logger.error(f"[ShortlistController] Error fetching job round overview: {e}", exc_info=True)
        return ResponseBuilder.server_error("Unable to fetch job round overview. Please retry later.")


async def get_all_candidates_controller(
    job_id: str,
    round_id: str,
    result_filter: Optional[str],
    db: AsyncSession
) -> StandardResponse:
    try:
        _validate_uuid(job_id, "job_id")
        _validate_uuid(round_id, "round_id")

        import inspect
        service = ShortlistService(db_session=db)
        maybe_candidates = service.get_candidates_by_job_and_round(job_id, round_id, result_filter)
        if inspect.isawaitable(maybe_candidates):
            candidates = await maybe_candidates
        else:
            candidates = maybe_candidates

        if not candidates:
            return ResponseBuilder.error(
                message="No candidates found for the provided job or round.",
                errors=["No such job post found or round not found in database."],
                status_code=status.HTTP_404_NOT_FOUND
            )

        message = f"Fetched candidates for job {job_id}, round {round_id}."
        if result_filter and result_filter.lower() != "all":
            message = f"Fetched {result_filter.lower()} candidates for job {job_id}, round {round_id}."

        return ResponseBuilder.success(
            message=message,
            data={"candidates": candidates},
            status_code=status.HTTP_200_OK
        )

    except HTTPException as e:
        return ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code)
    except Exception as e:
        logger.error(f"[ShortlistController] Error fetching candidates for job {job_id}, round {round_id}: {e}", exc_info=True)
        return ResponseBuilder.server_error("Failed to fetch candidates. Please retry later.")


async def update_candidate_status_controller(
    profile_id: str,
    round_id: str,
    input: UpdateShortlistRequest,
    db: AsyncSession
) -> StandardResponse:
    try:
        _validate_uuid(profile_id, "profile_id")
        _validate_uuid(round_id, "round_id")

        import inspect
        service = ShortlistService(db_session=db)
        maybe_update = service.update_candidate_status(profile_id, round_id, input)
        if inspect.isawaitable(maybe_update):
            update_result = await maybe_update
        else:
            update_result = maybe_update

        if not update_result:
            return ResponseBuilder.error(
                message="Unable to update result. Please retry later.",
                errors=["Patch process failed unexpectedly."],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return ResponseBuilder.success(
            message=f"Candidate status updated to '{input.new_result}' for round {round_id}.",
            data={"updated_candidate": update_result},
            status_code=status.HTTP_200_OK
        )

    except HTTPException as e:
        return ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code)
    except Exception as e:
        logger.error(f"[ShortlistController] Error updating candidate status: {e}", exc_info=True)
        return ResponseBuilder.server_error("Unable to update result. Please retry later.")
