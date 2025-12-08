# app/api/v1/shortlist_routes.py

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, status, Depends, Path, Query

from app.db.connection_manager import get_db
from app.schemas.standard_response import StandardResponse
from app.controllers.shortlist_controller import (
    get_job_round_overview_controller,
    get_all_candidates_controller,
    update_candidate_status_controller, 
)
from app.schemas.update_shortlist_request import UpdateShortlistRequest

shortlist_routes_router = APIRouter(prefix="/shortlist", tags=["Shortlist"])

@shortlist_routes_router.get(
    "/overview",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job with Round Overview"
)
async def get_job_round_overview_route(
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all jobs and their round overviews."""
    return await get_job_round_overview_controller(db=db)


@shortlist_routes_router.get(
    "/{job_id}/rounds/{round_id}/candidates",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Candidates in a Specific Job Round"
)
async def get_all_candidates_route(
    job_id: str = Path(..., description="UUID of the Job Post"),
    round_id: str = Path(..., description="UUID of the Interview Round"),
    result_filter: Optional[str] = Query(None, description="Filter by result type"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all candidates for a specific job and round."""
    return await get_all_candidates_controller(
        job_id=job_id,
        round_id=round_id,
        result_filter=result_filter,
        db=db
    )


@shortlist_routes_router.patch(
    "/rounds/{round_id}/candidates/{profile_id}/status",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate status (shortlist/reject/under_review)"
)
async def update_candidate_status_route(
    input: UpdateShortlistRequest,
    round_id: str = Path(..., description="UUID of the Interview Round"),
    profile_id: str = Path(..., description="UUID of the candidate's Profile"),
    db: AsyncSession = Depends(get_db)
):
    """Update a candidate's shortlist/reject/under_review result."""
    return await update_candidate_status_controller(
        profile_id=profile_id,
        round_id=round_id,
        input=input,
        db=db
    )