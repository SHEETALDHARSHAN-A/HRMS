# app/api/v1/scheduling_routes.py
from fastapi import APIRouter, Request, HTTPException, Depends
from app.db.connection_manager import get_db # Need this import to resolve dependency
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest
from app.schemas.scheduling_interview_request import RescheduleInterviewRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.controllers.scheduling_controller import (
    scheduling_interview_controller,
    get_scheduled_interviews_controller,
    reschedule_interview_controller,
)
from app.utils.standard_response_utils import ResponseBuilder
from app.schemas.standard_response import StandardResponse
from fastapi.responses import JSONResponse 
from app.schemas.standard_response import StandardResponse
from app.utils.standard_response_utils import ResponseBuilder

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])
 
@router.post(
    "/schedule-interview",
    summary="Schedule interview for a candidate batch",
    response_model=StandardResponse,
    description="""
    Schedule interview for a shortlisted candidate batch.
    - Accepts job_uuid and a list of profile_ids, date, and time in the request body
    - Sends email with calendar invite and unique token
    - Fails gracefully if already scheduled or invalid
    """
)
async def schedule_interview_route(
    request: Request,
    interview_request: SchedulingInterviewRequest,
    db: AsyncSession = Depends(get_db) # Dependency injection
):
    """Handles the scheduling request."""
    result = await scheduling_interview_controller(
        request=request,
        interview_request=interview_request,
        db=db
    )
    # Return JSONResponse using the status code from the controller's dict output
    return JSONResponse(content=result, status_code=result.get("status_code"))


@router.get("/scheduled-interviews", summary="Get all scheduled interviews", response_model=StandardResponse)
async def get_scheduled_interviews_route(
    job_id: str,
    round_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Fetches all scheduled interviews."""
    result = await get_scheduled_interviews_controller(
        job_id=job_id,
        round_id=round_id,
        db=db
    )
    return JSONResponse(content=result, status_code=result.get("status_code"))


@router.post(
    "/reschedule-interview",
    summary="Reschedule an existing interview",
    response_model=StandardResponse,
    description="""
    Reschedule an already scheduled interview.
    - Accepts either interview token, OR job_id + profile_id + round_id.
    - Supports both candidate-side (token) and HR-side (identity) rescheduling.
    - Increments reschedule count and updates schedule status.
    - Sends updated invitation email to candidate.
    """,
)
async def reschedule_interview_route(
    request: Request,
    reschedule_request: RescheduleInterviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Handles interview reschedule requests."""
    result = await reschedule_interview_controller(
        request=request,
        reschedule_request=reschedule_request,
        db=db,
    )
    return JSONResponse(content=result, status_code=result.get("status_code"))


