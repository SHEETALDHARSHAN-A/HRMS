# RMS-Backend-dev-sheetal/app/api/v1/job_post_routes.py
from typing import Optional
from fastapi.responses import JSONResponse
from fastapi import APIRouter, UploadFile, File, status, Query, Depends, Path, Request, Header, HTTPException

from app.db.connection_manager import get_db
from app.config.app_config import AppConfig
from app.schemas.update_jd_request import UpdateJdRequest
from app.schemas.standard_response import StandardResponse
from app.schemas.analyze_jd_request import AnalyzeJdRequest
from app.utils.standard_response_utils import ResponseBuilder
from app.controllers.job_post_controller import (
    upload_job_post_controller,
    analyze_job_details_controller,
    update_job_post_controller,
    get_job_post_uploader,
    get_all_jobs_controller,
    get_my_jobs_controller,
    get_active_jobs_controller,
    get_job_by_id_controller,
    get_public_job_by_id_controller,
    toggle_job_status_controller,
    delete_job_post_controller,
    delete_job_posts_batch_controller,
    candidate_stats_controller,
    search_public_jobs_controller,
    get_search_suggestions_controller,
    get_public_search_service,
    get_my_agent_jobs_controller,
)

 
job_post_routes_router = APIRouter(prefix="/job-post", tags=["Job Post"])
 
 
def _verify_internal_token(x_internal_token: str | None = Header(None)) -> bool:
    """Verify an internal service token provided in the header `X-Internal-Token`.
    This is a lightweight protection to ensure only internal workers/curl calls can trigger
    event-driven evaluations. The token is read from `AppConfig().internal_service_token`.
    """
    config = AppConfig()
    if not config.internal_service_token:
        raise HTTPException(status_code=403, detail="Internal evaluate endpoint is disabled")
    if x_internal_token != config.internal_service_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True

# ------------------------------------------------------------------
# 1. AI & FILE OPERATIONS
# ------------------------------------------------------------------
@job_post_routes_router.post(
    "/analyze",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Job Description using LLM Agent"
)
async def analyze_job_details_route(
    job_details: AnalyzeJdRequest
):
    """Analyze a job title and description using the LLM agent."""
    return await analyze_job_details_controller(job_details=job_details)
 
 
# ------------------------------------------------------------------
# 2. UPLOAD JD
# ------------------------------------------------------------------
@job_post_routes_router.post(
    "/upload",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload JD File and Extract/Save Content"
)
async def upload_job_post_route(    
    file: UploadFile = File(...),
    jd_uploader = Depends(get_job_post_uploader)
):
    """Upload a job description file (DOCX/PDF), extract its content."""
    return await upload_job_post_controller(
        file=file,
        jd_uploader=jd_uploader
    )
 
# ------------------------------------------------------------------
# 2. CRUD OPERATIONS (INTERNAL/ADMIN)
# ------------------------------------------------------------------
@job_post_routes_router.post(
    "/update",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or Update Job Post"
)
async def update_job_post_route(
    job_details: UpdateJdRequest,
    request: Request
):
    """
    Creates a new job post (if job_id is None) or updates an existing one
    (if job_id is provided in the body).
    """
    try:

        if not getattr(getattr(request, 'state', None), 'user', None):
            test_user = request.headers.get('X-Test-User')
            if test_user:
                request.state.user = {"user_id": test_user, "sub": test_user}
        job_id_from_body = job_details.job_id
        result = await update_job_post_controller(
            job_details=job_details,
            job_id=job_id_from_body,
            request=request,
        )


        # Controller returns a dict including status_code; forward it as JSONResponse so HTTP status matches
        if isinstance(result, dict):
            resp_status = result.get("status_code", status.HTTP_200_OK)
            return JSONResponse(content=result, status_code=resp_status)
        return result
    except Exception as e:
        print(f"Error in update endpoint: {str(e)}")
        return ResponseBuilder.server_error(f"An unexpected error occurred: {str(e)}")


# ------------------------------------------------------------------
# 4. GET ALL JOB POSTS (ADMIN/INTERNAL)
# ------------------------------------------------------------------
@job_post_routes_router.get(
    "/all",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all job posts (admin)"
)
async def get_all_job_posts_route(request: Request):
    """Retrieves all job posts in the system for admin view."""
    return await get_all_jobs_controller(request=request)
 
@job_post_routes_router.get(
    "/my-jobs",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get jobs created by current user"
)
async def get_my_job_posts_route(request: Request):
    """Retrieves job posts created by the currently authenticated user."""
    return await get_my_jobs_controller(request)
@job_post_routes_router.get(
    "/my-agent-jobs",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get agent-enabled jobs for current user"
)
async def get_my_agent_jobs_route(request: Request):
    """Retrieves agent-enabled job posts created by the currently authenticated user."""
    return await get_my_agent_jobs_controller(request)
@job_post_routes_router.get(
    "/get-job-by-id/{job_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job by id"
)
async def get_job_by_id_route(job_id: str, request: Request):
    """Retrieves full details for a single job post by ID."""
    return await get_job_by_id_controller(job_id=job_id, request=request)
 
@job_post_routes_router.patch(
    "/{job_id}/toggle-status",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle job status"
)
async def toggle_job_status_route(job_id: str, is_active: bool = Query(False), request: Request = None):
    """Toggles the 'is_active' status of a job post. Request is passed for permission checks."""
    # Allow tests to set the user via header if middleware is not present.
    if request is not None and not getattr(getattr(request, 'state', None), 'user', None):
        test_user = request.headers.get('X-Test-User')
        if test_user:
            request.state.user = {"user_id": test_user, "sub": test_user}

    return await toggle_job_status_controller(job_id=job_id, is_active=is_active, request=request)
 
@job_post_routes_router.delete(
    "/delete-job-by-id/{job_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete job by id (soft)"
)
async def delete_job_by_id_route(job_id: str, request: Request = None):
    """Soft-deletes (marks inactive) a single job post by ID. Request is passed for permission checks."""
    # Allow tests to set the user via header if middleware is not present.
    if request is not None and not getattr(getattr(request, 'state', None), 'user', None):
        test_user = request.headers.get('X-Test-User')
        if test_user:
            request.state.user = {"user_id": test_user, "sub": test_user}

    return await delete_job_post_controller(job_id=job_id, request=request)
 
@job_post_routes_router.post(
    "/delete-batch",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch delete jobs (permanent)"
)
async def delete_jobs_batch_route(job_ids: dict, request: Request = None):
    """Permanently deletes multiple jobs and all related records by a list of IDs. Request is passed for permission checks."""
    ids = job_ids.get("job_ids") if isinstance(job_ids, dict) else job_ids
    return await delete_job_posts_batch_controller(job_ids=ids, request=request)
 
@job_post_routes_router.get(
    "/candidate-stats/{job_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Candidate stats for job"
)
async def candidate_stats_route(job_id: str):
    """Retrieves aggregated candidate counts (applied, shortlisted, etc.) for a job."""
    return await candidate_stats_controller(job_id=job_id)
 
# ------------------------------------------------------------------
# 3. PUBLIC ROUTES (Search, Listings, Detail)
# ------------------------------------------------------------------
@job_post_routes_router.get(
    "/active",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active job posts for career page"
)
async def get_active_job_posts_route():
    """Retrieves all active job posts for public viewing."""
    return await get_active_jobs_controller()
 
@job_post_routes_router.get(
    "/public/job/{job_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public job details for application"
)
async def get_public_job_details_route(job_id: str):
    """Retrieves trimmed details for an active job post, used on the public application page."""
    return await get_public_job_by_id_controller(job_id=job_id)
 
@job_post_routes_router.get(
    "/public/search-suggestions",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get autocomplete suggestions for public search"
)
async def get_search_suggestions_route(
    search_service = Depends(get_public_search_service)
):
    """Provides a list of all unique skills and locations in the DB to power the search box autocomplete."""
    return await get_search_suggestions_controller(search_service=search_service)
 
@job_post_routes_router.get(
    "/public/search",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Search active jobs with ranked results"
)
async def search_public_jobs_route(
    role: Optional[str] = Query(None, alias="role", description="Job title/role query"),
    skills: Optional[str] = Query(None, alias="skills", description="Comma-separated list of skills"),
    locations: Optional[str] = Query(None, alias="locations", description="Comma-separated list of locations"),
    search_service = Depends(get_public_search_service)
):
    """
    Searches all active jobs based on role, skills, and/or locations.
    Returns a ranked list of jobs, with the best matches first.
    At least one query parameter must be provided.
    """
    return await search_public_jobs_controller(
        search_service=search_service,
        role=role,
        skills=skills,
        locations=locations
    )
