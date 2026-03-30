import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection_manager import get_db
from app.schemas.coding_request import CodingSubmitRequest
from app.schemas.standard_response import StandardResponse
from app.services.coding_service import CodingService
from app.utils.standard_response_utils import ResponseBuilder


logger = logging.getLogger(__name__)

coding_router = APIRouter(prefix="/coding", tags=["Coding Interview"])


@coding_router.get(
    "/question",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get assessment question for candidate",
)
async def get_coding_question_route(
    token: str = Query(..., description="Interview token"),
    email: EmailStr = Query(..., description="Candidate email"),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = CodingService(db)
        question = await service.get_question(token=token, email=str(email))
        return ResponseBuilder.success(message="Coding question fetched.", data=question)
    except HTTPException as exc:
        return ResponseBuilder.error(message=exc.detail, status_code=exc.status_code)
    except Exception as exc:
        logger.error("Error fetching coding question: %s", exc, exc_info=True)
        return ResponseBuilder.server_error("Unable to fetch coding question.")


@coding_router.post(
    "/submit",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit coding or MCQ assessment for evaluation",
)
async def submit_coding_solution_route(
    request: CodingSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        service = CodingService(db)
        submission = await service.submit_solution(request)
        return ResponseBuilder.success(message="Submission evaluated.", data=submission)
    except HTTPException as exc:
        return ResponseBuilder.error(message=exc.detail, status_code=exc.status_code)
    except Exception as exc:
        logger.error("Error submitting coding solution: %s", exc, exc_info=True)
        return ResponseBuilder.server_error("Unable to evaluate coding submission.")


@coding_router.get(
    "/submission/{submission_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get assessment submission and evaluation",
)
async def get_coding_submission_route(
    submission_id: str,
    token: str = Query(..., description="Interview token"),
    email: EmailStr = Query(..., description="Candidate email"),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = CodingService(db)
        submission = await service.get_submission(submission_id=submission_id, token=token, email=str(email))
        return ResponseBuilder.success(message="Submission fetched.", data=submission)
    except HTTPException as exc:
        return ResponseBuilder.error(message=exc.detail, status_code=exc.status_code)
    except Exception as exc:
        logger.error("Error fetching coding submission: %s", exc, exc_info=True)
        return ResponseBuilder.server_error("Unable to fetch coding submission.")
