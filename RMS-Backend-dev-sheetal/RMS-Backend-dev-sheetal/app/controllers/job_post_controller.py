# app/controllers/job_post_controller.py

import logging
import inspect
import uuid as _uuid
import redis.asyncio as redis

from sqlalchemy import update
from pydantic import BaseModel
from types import SimpleNamespace
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse
from fastapi import UploadFile, Depends, HTTPException, File, status, Request, Query

from app.utils.standard_response_utils import ResponseBuilder 

from app.schemas.update_jd_request import UpdateJdRequest 
from app.schemas.standard_response import StandardResponse
from app.schemas.analyze_jd_request import AnalyzeJdRequest

# `GetJobPost` is optionally imported via a compatibility shim below.
# Avoid importing it here at module import time to allow tests to stub
# `app.services.job_post.get_job_post` with various exported symbols.
from app.services.job_post.job_post_serializer import serialize_admin_job
from app.services.job_post.job_post_reader import JobPostReader
from app.services.job_post.job_post_permissions import JobPostPermissions
from app.services.job_post.update_jd.update_job_post import UpdateJobPost 
from app.services.job_post.upload_jd.upload_job_post import UploadJobPost 
from app.services.job_post.public_search_service import PublicSearchService
from app.services.job_post.analyze_jd.analyze_job_post import AnalyzeJobPost

from app.db.connection_manager import get_db
from app.db.redis_manager import get_redis_client 
from app.db.models.job_post_model import JobDetails
from app.db.repository.job_post_repository import (
    set_job_active_status,
    soft_delete_job_by_id,
    soft_delete_jobs_batch,
    hard_delete_job_by_id,
    hard_delete_jobs_batch,
    get_agent_jobs_by_user_id,
)

# Keep a reference to repository functions that are patched in tests so static
# analysis tools don't mark these imports as unused. Tests patch these names
# via the module path (e.g. patch('app.controllers.job_post_controller.soft_delete_job_by_id')).
_TEST_PATCH_REFERENCES = (soft_delete_job_by_id, soft_delete_jobs_batch)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _to_dict(obj: Any) -> Any:
    """Normalize Pydantic/BaseModel or other objects to plain dict if possible."""
    if obj is None:
        return None
    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except Exception:
            pass
    # Pydantic v1
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()
        except Exception:
            pass
    # already a dict
    if isinstance(obj, dict):
        return obj
    return obj


# Provide a small compatibility shim for GetJobPost which some tests patch
try:
    # If the project provides a GetJobDetails symbol, use a thin
    # synchronous wrapper class that matches historical controller
    # behavior (accepts `db_session` and exposes a non-async fetch).
    from app.services.job_post.get_job_post import GetJobDetails as _ImportedGetJobDetails

    class GetJobPost:
        def __init__(self, db_session):
            self.db = db_session
            # If the imported service provides an implementation, keep
            # an instance of it and delegate calls to preserve behavior
            # from the real service (or the test stub).
            try:
                self._impl = _ImportedGetJobDetails(db_session)
            except Exception:
                self._impl = None

        def fetch_full_job_details(self, job_id: str):
            # Prefer delegating to the imported service implementation
            if self._impl is not None and hasattr(self._impl, 'fetch_full_job_details'):
                return self._impl.fetch_full_job_details(job_id)

            # Fallback to the reader if the imported impl isn't available
            reader = JobPostReader(self.db)
            candidate = reader.get_job(job_id=job_id)
            return candidate
except Exception:
    # Fallback compatibility shim used when the real service isn't importable.
    # This supports both sync and async `JobPostReader.get_job` implementations
    # by awaiting the result when necessary. The constructor accepts either
    # `db` or `db_session` to be lenient with callers/tests.
    class GetJobPost:
        def __init__(self, db=None, db_session=None):
            self.db = db if db is not None else db_session

        async def fetch_full_job_details(self, job_id: str):
            reader = JobPostReader(self.db)
            candidate = reader.get_job(job_id=job_id)
            return await candidate if inspect.isawaitable(candidate) else candidate

# ------------------------------------------------------------------
# DEPENDENCIES (initialized inside controller)
# ------------------------------------------------------------------

def get_job_post_uploader(redis_client: redis.Redis = Depends(get_redis_client)) -> UploadJobPost:
    """Dependency to provide an initialized UploadJobPost service."""
    return UploadJobPost(redis_store=redis_client)


async def get_public_search_service(db: Any = Depends(get_db)) -> PublicSearchService:
    """Dependency to provide an initialized PublicSearchService.

    Note: FastAPI executes async generator dependencies like `get_db` and
    injects the yielded value (an `AsyncSession`) directly. The previous
    implementation attempted to `async for` over `db`, but `db` is already
    an `AsyncSession` instance here which raised the ``__aiter__`` error.
    """
    try:
        # `db` is the AsyncSession provided by the `get_db` dependency
        return PublicSearchService(db_session=db)
    except Exception as e:
        logger.error(f"Failed to get DB for PublicSearchService: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")
# OPTIMIZED: Centralized helper for retrieving current user data
def _get_current_user(request: Request) -> Dict[str, Any] | None:
    """Extracts user information set by the JWT middleware."""
    request_state = getattr(request, "state", None)
    current_user = getattr(request_state, "user", None)
    
    if isinstance(current_user, dict):
        # Normalize user_id extraction
        current_user["user_id"] = current_user.get("user_id") or current_user.get("sub")
        return current_user
    return None

# OPTIMIZED: Centralized error handling for controller catch-all
def _handle_controller_exception(e: Exception, job_id: str | None = None, operation: str = "operation") -> JSONResponse:
    """Logs the exception and returns a generic 500 JSONResponse."""
    log_message = f"Error during job post {operation}"
    if job_id:
        log_message += f" for job {job_id}"
        
    logger.error(f"{log_message}: {e}", exc_info=True)
    
    # NOTE: Retaining the original behavior of leaking the exception message (f"...")
    # for 500 errors, as per the constraint to maintain functionality.
    return JSONResponse(
        content=ResponseBuilder.server_error(f"An unexpected error occurred during the {operation}: {e}"),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


# ------------------------------------------------------------------
# 1. UPLOAD JOB POST
# ------------------------------------------------------------------
async def upload_job_post_controller(
    file: UploadFile = File(...),
    jd_uploader: UploadJobPost = Depends(get_job_post_uploader)
) -> StandardResponse:
    """
    Handles file upload and saves extracted data, with improved error handling.
    """
    try:
        service_result: Dict[str, Any] = await jd_uploader.job_details_file_upload(file=file)
        
        # --- Handle Service-Level Failure (LLM/Cache Errors) ---
        if "error" in service_result:
            # We assume extraction errors (LLM validation failure, API quota, etc.)
            return ResponseBuilder.error(
                message=service_result.get("error", "Extraction failed."),
                errors=[service_result.get("error", "Extraction failed.")],
                status_code=status.HTTP_400_BAD_REQUEST # Return 400 for bad client request/predictable failure
            )
        
        # --- Handle Success ---
        if "job_details" in service_result:
            job_details: Any = service_result.get("job_details")
            return ResponseBuilder.success(
                message=f"Job details extracted.",
                data={"extracted_details": job_details},
                status_code=status.HTTP_200_OK
            )
            
        # Fallback for unexpected service return structure
        return ResponseBuilder.server_error("JD extraction failed: Unexpected service output format.")
        
    except Exception as e:
        return _handle_controller_exception(e, operation="file processing")


# ------------------------------------------------------------------
# 2. UPDATE JOB POST (UPSERT)
# ------------------------------------------------------------------
async def update_job_post_controller(
    job_details: UpdateJdRequest,
    job_id = None,
    request: Request = None,
) -> JSONResponse:
    """
    Update an existing job post or create a new one if job_id is not provided.
    """
    job_id_from_body = getattr(job_details, 'job_id', None)
    final_job_id = job_id or job_id_from_body

    try:
        # Extract authenticated user from request.state (set by JWT middleware)
        # Be defensive when `request` is None (unit tests may pass None).
        request_state = getattr(request, 'state', None) if request is not None else None
        user_payload = getattr(request_state, 'user', None)
        user_id = None
        if user_payload:
            user_id = user_payload.get("sub") # "sub" holds the user's UUID
        
        if not user_id:
            return ResponseBuilder.error(
                message="Unauthorized: User information missing.",
                errors=["User authentication required."],
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        async for db in get_db(): 
            # Debug: print incoming job_details (Pydantic model) to help trace update issues
            try:
                print(f"[DEBUG CONTROLLER] update_job_post_controller received payload: {job_details.model_dump()}")
            except Exception:
                print("[DEBUG CONTROLLER] Could not dump job_details payload for logging")
            
            job_id_from_body = getattr(job_details, 'job_id', None)
            final_job_id = job_id or job_id_from_body

            # Extract authenticated user id from app state set by JWT middleware (if present)
            request_user = getattr(request, "state", None)
            current_user = getattr(request_user, "user", None) if request_user else None
            creator_id = None
            if isinstance(current_user, dict):
                creator_id = current_user.get("user_id") or current_user.get("sub")

            # Check permissions for updates
            if final_job_id:
                reader = JobPostReader(db)
                # Support both async and sync reader implementations (tests often patch sync returns)
                existing_job_candidate = reader.get_job(job_id=final_job_id)
                existing_job_data = await existing_job_candidate if inspect.isawaitable(existing_job_candidate) else existing_job_candidate
                if existing_job_data:
                    from types import SimpleNamespace
                    mock_job = SimpleNamespace()
                    mock_job.user_id = existing_job_data.get("user_id") or existing_job_data.get("created_by_user_id")

                    if not JobPostPermissions.can_edit_job(mock_job, current_user):
                        error_payload = ResponseBuilder.error(
                            message="You don't have permission to edit this job post",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
                        return JSONResponse(content=error_payload, status_code=status.HTTP_403_FORBIDDEN)
                else:
                    error_payload = ResponseBuilder.error(message="Job not found", status_code=status.HTTP_404_NOT_FOUND)
                    return JSONResponse(content=error_payload, status_code=status.HTTP_404_NOT_FOUND)
            
            update_job_post_service = UpdateJobPost(db=db)

            service_candidate = update_job_post_service.update_job_post(
                job_details=job_details,
                job_id=final_job_id,
                creator_id=creator_id,
            )
            service_result_raw = await service_candidate if inspect.isawaitable(service_candidate) else service_candidate



            # Normalize service result (accept dicts or Pydantic models)
            if hasattr(service_result_raw, 'model_dump'):
                service_result = service_result_raw.model_dump()
            elif hasattr(service_result_raw, 'dict'):
                service_result = service_result_raw.dict()
            elif hasattr(service_result_raw, '__dict__'):
                # Handle StandardResponse or similar objects with attributes
                service_result = {
                    'success': getattr(service_result_raw, 'success', None),
                    'message': getattr(service_result_raw, 'message', None),
                    'data': getattr(service_result_raw, 'data', None),
                    'status_code': getattr(service_result_raw, 'status_code', None)
                }
            else:
                service_result = service_result_raw

            # Debug: log the service result for tracing
            try:
                if isinstance(service_result, dict) and service_result.get('job_details'):
                    job_details_response = service_result.get('job_details', {})
            except Exception as e:
                logger.exception("Error parsing service_result job_details: %s", e)

            success_flag = None
            if isinstance(service_result, dict) and 'success' in service_result:
                success_flag = service_result.get('success')



            if success_flag is False:
                return ResponseBuilder.error(
                    message=(service_result.get('message') if isinstance(service_result, dict) else 'Failed to update job post.'),
                    errors=(service_result.get('errors') if isinstance(service_result, dict) else None),
                    status_code=(service_result.get('status_code') if isinstance(service_result, dict) else status.HTTP_500_INTERNAL_SERVER_ERROR)
                )

            action = "updated" if final_job_id else "created"
            # prefer service-provided status code if present
            status_code = (service_result.get('status_code') if isinstance(service_result, dict) and service_result.get('status_code') else (status.HTTP_200_OK if final_job_id else status.HTTP_201_CREATED))

            # Try to read returned job_details from known shapes
            job_details_payload = None
            if isinstance(service_result, dict):
                job_details_payload = service_result.get('data') or service_result.get('job_details') or (service_result.get('data', {}).get('job_details') if isinstance(service_result.get('data'), dict) else None)

            return ResponseBuilder.success(
                message=f"Job post successfully {action}.",
                data={"job_details": job_details_payload},
                status_code=status_code
            )
    except HTTPException as e:
        error_payload = ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code)
        return JSONResponse(content=error_payload, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error during job post update: {e}", exc_info=True)
        return ResponseBuilder.server_error(
            f"An unexpected error occurred while updating the job post: {e}"
        )
 
def get_analyze_jd_service() -> AnalyzeJobPost:
    """Return AnalyzeJobPost service."""
    return AnalyzeJobPost()
 
# ------------------------------------------------------------------
# 3. ANALYZE JOB POST
# ------------------------------------------------------------------
async def analyze_job_details_controller(job_details: AnalyzeJdRequest) -> StandardResponse:
    try:
        jd_analyzer = get_analyze_jd_service()
        analysis_data = await jd_analyzer.analyze_job_details(job_details=job_details)
 
        return ResponseBuilder.success(
            message="Job analysis successful.",
            data={"analysis_result": analysis_data},
            status_code=status.HTTP_200_OK
        )
    except HTTPException as e:
        return ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"An unexpected error occurred during analysis: {e}")
 
async def get_all_jobs_controller(request: Request = None) -> StandardResponse:
    """Return all job posts (internal/admin view)."""
    try:
        async for db in get_db():
            reader = JobPostReader(db)
            jobs_candidate = reader.list_all()
            jobs = await jobs_candidate if inspect.isawaitable(jobs_candidate) else jobs_candidate
            
            current_user = _get_current_user(request)
            jobs = JobPostPermissions.filter_jobs_by_ownership(jobs, current_user)
            
            return ResponseBuilder.success(message="Fetched all job posts.", data={"jobs": jobs})
    except Exception as e:
        return _handle_controller_exception(e, operation="fetch all jobs")


async def get_my_jobs_controller(request: Request) -> StandardResponse:
    """Return only jobs created by the current user."""
    current_user = _get_current_user(request)
    
    if not current_user:
        return ResponseBuilder.error(
            message="Authentication required", 
            errors=["Authentication required"],
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    user_id = current_user.get("user_id")
    if not user_id:
        return ResponseBuilder.error(
            message="User ID not found in token.", 
            errors=["User ID not found in token."],
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    try:
        async for db in get_db():
            reader = JobPostReader(db)
            jobs_candidate = reader.list_all()
            jobs = await jobs_candidate if inspect.isawaitable(jobs_candidate) else jobs_candidate
            
            # OPTIMIZED: Use the efficient DB-filtered query
            job_orms = await reader.list_by_user(user_id) 
            
            # The list is already filtered by user_id, but running this ensures permission flags are set.
            jobs = JobPostPermissions.filter_jobs_by_ownership(job_orms, current_user, show_own_only=True)
            
            return ResponseBuilder.success(message="Fetched your job posts.", data={"jobs": jobs})
    except Exception as e:
        return _handle_controller_exception(e, operation="fetch my jobs")

async def get_my_agent_jobs_controller(request: Request) -> StandardResponse:
    """Return only jobs created by the current user that are agent-enabled."""
    current_user = _get_current_user(request)
    
    if not current_user:
        return ResponseBuilder.error(
            message="Authentication required", 
            errors=["Authentication required"],
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    user_id = current_user.get("user_id")
    if not user_id:
        return ResponseBuilder.error(
            message="User ID not found in token.", 
            errors=["User ID not found in token."],
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    try:
        async for db in get_db():
            job_orms = await get_agent_jobs_by_user_id(db, user_id)
            
            # Use the serializer to convert ORM objects into API-friendly dicts
            reader = JobPostReader(db)
            jobs_list = [serialize_admin_job(job) for job in job_orms]
            
            # The JobPostReader doesn't know about agent_configs, so we add it manually.
            # This is a fast way to get the data to the frontend.
            for i, job in enumerate(jobs_list):
                job["agentRounds"] = [
                    {
                        "id": config.id,
                        "jobId": config.job_id,
                        "roundListId": config.round_list_id,
                        "roundName": config.round_name,
                        "roundFocus": config.round_focus,
                        "persona": config.persona,
                        "keySkills": config.key_skills,
                        "customQuestions": config.custom_questions,
                        "forbiddenTopics": config.forbidden_topics,
                        # New per-round fields
                        "interview_mode": getattr(config, 'interview_mode', None) or getattr(config, 'interviewMode', None) or 'agent',
                        "interview_time": getattr(config, 'interview_time', None) or getattr(config, 'interviewTime', None),
                        "interviewer_id": getattr(config, 'interviewer_id', None) or getattr(config, 'interviewerId', None),
                        # Coding challenge fields
                        "codingEnabled": bool(getattr(config, 'coding_enabled', False)),
                        "codingQuestionMode": getattr(config, 'coding_question_mode', 'ai') or 'ai',
                        "codingDifficulty": getattr(config, 'coding_difficulty', 'medium') or 'medium',
                        "codingLanguages": getattr(config, 'coding_languages', None) or ['python'],
                        "providedCodingQuestion": getattr(config, 'provided_coding_question', None),
                        "codingTestCaseMode": getattr(config, 'coding_test_case_mode', 'ai') or 'ai',
                        "codingTestCases": getattr(config, 'coding_test_cases', None) or [],
                        "codingStarterCode": getattr(config, 'coding_starter_code', None) or {},
                        "mcqEnabled": bool(getattr(config, 'mcq_enabled', False)),
                        "mcqQuestionMode": getattr(config, 'mcq_question_mode', 'ai') or 'ai',
                        "mcqDifficulty": getattr(config, 'mcq_difficulty', 'medium') or 'medium',
                        "mcqQuestions": getattr(config, 'mcq_questions', None) or [],
                        "mcqPassingScore": getattr(config, 'mcq_passing_score', 60),
                    } for config in job_orms[i].agent_configs
                ]

            return ResponseBuilder.success(message="Fetched your agent-enabled job posts.", data={"jobs": jobs_list})
    except Exception as e:
        return _handle_controller_exception(e, operation="fetch my agent jobs")
        
async def get_active_jobs_controller() -> StandardResponse:
    """Return active job posts for the career page (public view)."""
    try:
        async for db in get_db():
            reader = JobPostReader(db)
            jobs_candidate = reader.list_active()
            jobs = await jobs_candidate if inspect.isawaitable(jobs_candidate) else jobs_candidate

            try:
                logger.info(
                    "[job_controller] get_active_jobs_controller returning %s jobs. sample_ids=%s",
                    len(jobs),
                    [str(job.get("job_id")) for job in jobs[:5]],
                )
            except Exception:
                pass

            return ResponseBuilder.success(message="Fetched active job posts.", data={"jobs": jobs})
    except Exception as e:
        return _handle_controller_exception(e, operation="fetch active jobs")


async def get_job_by_id_controller(job_id: str, request: Request = None) -> StandardResponse:
    try:
        # OPTIMIZED: Validate UUID early to return a clear 400 error instead of a 500 leak
        try:
            job_uuid = _uuid.UUID(job_id)
        except ValueError:
            return ResponseBuilder.error(
                message="Invalid job ID format. Must be a valid UUID.", 
                errors=["Invalid job ID format. Must be a valid UUID."], 
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        async for db in get_db():
            # Prefer higher-level GetJobPost service when available (tests patch this class)
            try:
                get_job_service = GetJobPost(db)
                job_candidate = get_job_service.fetch_full_job_details(job_id)
                job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
            except Exception:
                reader = JobPostReader(db)
                job_candidate = reader.get_job(job_id=job_id)
                job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
            if not job_payload:
                return ResponseBuilder.error(message="Job not found", errors=["Job not found"], status_code=status.HTTP_404_NOT_FOUND)

            current_user = _get_current_user(request)
            
            # OPTIMIZED: Use SimpleNamespace mock for permission check
            mock_job = SimpleNamespace(
                user_id=job_payload.get("user_id") or job_payload.get("created_by_user_id")
            )
            
            job_payload["can_edit"] = JobPostPermissions.can_edit_job(mock_job, current_user)
            user_id = current_user.get("user_id") if current_user else None
            job_payload["is_own_job"] = user_id and str(mock_job.user_id) == str(user_id)

            # Controllers should avoid exposing internal FK values in responses by default
            job_payload.pop("user_id", None)

            return ResponseBuilder.success(message="Fetched job.", data={"job": job_payload})
            
    except Exception as e:
        return _handle_controller_exception(e, job_id=job_id, operation="fetch job by id")


async def get_public_job_by_id_controller(job_id: str) -> StandardResponse:
    """
    Public endpoint to get job details for job application page.
    No authentication required, returns only public job information.
    """
    try:
        async for db in get_db():
            reader = JobPostReader(db)
            job_candidate = reader.get_job(job_id=job_id)
            job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
            if not job_payload:
                return ResponseBuilder.error(message="Job not found", status_code=404)

            # Check if job is active (public jobs should only show active ones)
            if not job_payload.get("is_active", False):
                return ResponseBuilder.error(message="Job not available", status_code=404)

            # Remove sensitive fields for public access and map correct field names
            public_fields = {
                "job_id": job_payload.get("job_id"),
                "title": job_payload.get("job_title"),
                "location": job_payload.get("job_location"), 
                "wfh": job_payload.get("work_from_home", False),
                "skills": [skill.get("skill") for skill in job_payload.get("skills_required", [])] if job_payload.get("skills_required") else [],
                "min_experience": job_payload.get("minimum_experience"),
                "max_experience": job_payload.get("maximum_experience"),
                "salary": job_payload.get("salary"),
                "job_description": job_payload.get("job_description"),
                "qualifications": job_payload.get("qualifications"),
                "responsibilities": job_payload.get("responsibilities"),
                "benefits": job_payload.get("benefits"),
                "employment_type": job_payload.get("employment_type"),
                "department": job_payload.get("department"),
                "posted_date": job_payload.get("posted_date"),
                "is_active": job_payload.get("is_active")
            }

            return ResponseBuilder.success(message="Fetched public job details.", data={"job": public_fields})
    except Exception as e:
        logger.error(f"Error fetching public job by id: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"Failed to fetch job: {e}")


async def toggle_job_status_controller(job_id: str, is_active: bool, request: Request = None) -> StandardResponse:
    try:
        async for db in get_db():
            # Permission check: ensure current user can toggle this job
            request_user = getattr(request, "state", None) if request else None
            current_user = getattr(request_user, "user", None) if request_user else None

            reader = JobPostReader(db)
            job_candidate = reader.get_job(job_id=job_id)
            job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
            if not job_payload:
                return ResponseBuilder.error(message="Job not found", status_code=404)

            from types import SimpleNamespace
            mock_job = SimpleNamespace()
            mock_job.user_id = job_payload.get("user_id") or job_payload.get("created_by_user_id")

            if not JobPostPermissions.can_edit_job(mock_job, current_user):
                return ResponseBuilder.error(message="You don't have permission to toggle this job post", status_code=403)

            # Use service-layer UpdateJobPost (tests may patch this class)
            update_service = UpdateJobPost(db)
            toggle_candidate = update_service.toggle_status(job_id=job_id, is_active=is_active)
            toggle_result = await toggle_candidate if inspect.isawaitable(toggle_candidate) else toggle_candidate

            # If service returned a StandardResponse-like payload, forward it
            if hasattr(toggle_result, 'model_dump'):
                return toggle_result.model_dump()
            elif isinstance(toggle_result, dict):
                return toggle_result

            # Fallback to repository-based status update for non-service scenarios
            updated = await set_job_active_status(db, job_id=job_id, is_active=is_active)
            if not updated:
                return ResponseBuilder.error(message="Invalid job id or job not found", status_code=400)

            # reader will format payload as needed
            job_candidate = reader.get_job(job_id=job_id)
            job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
            if not job_payload:
                return ResponseBuilder.error(message="Job not found after update", errors=["Job not found after update"], status_code=status.HTTP_404_NOT_FOUND)

            return ResponseBuilder.success(
                message="Toggled job status.",
                data={"job_details": {"job_id": job_payload.get("job_id"), "is_active": bool(job_payload.get("is_active", False))}},
            )
    except Exception as e:
        return _handle_controller_exception(e, job_id=job_id, operation="toggle status")


async def delete_job_post_controller(job_id: str, request: Request = None) -> StandardResponse:
    """Permanently delete job post and all related records from database."""
    try:
        async for db in get_db():
            # Permission check: ensure current user can delete this job
            request_user = getattr(request, "state", None) if request else None
            current_user = getattr(request_user, "user", None) if request_user else None

            reader = JobPostReader(db)
            job_candidate = reader.get_job(job_id=job_id)
            job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
            if not job_payload:
                return ResponseBuilder.error(message="Job not found", status_code=404)

            from types import SimpleNamespace
            mock_job = SimpleNamespace()
            mock_job.user_id = job_payload.get("user_id") or job_payload.get("created_by_user_id")

            if not JobPostPermissions.can_edit_job(mock_job, current_user):
                return ResponseBuilder.error(message="You don't have permission to delete this job post", status_code=403)

            # Use service-layer UpdateJobPost for deletion
            update_service = UpdateJobPost(db)
            delete_candidate = update_service.delete_job_post(job_id)
            delete_result = await delete_candidate if inspect.isawaitable(delete_candidate) else delete_candidate

            # If service returned a StandardResponse-like payload, forward it
            if hasattr(delete_result, 'model_dump'):
                return delete_result.model_dump()
            elif isinstance(delete_result, dict):
                return delete_result

            # Should not reach here, but provide fallback
            return ResponseBuilder.success(message="Job deleted successfully.", data={"job_id": job_id})
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"Failed to delete job: {e}")


async def delete_job_posts_batch_controller(job_ids: list, request: Request = None) -> StandardResponse:
    """
    Batch-delete job posts (HARD DELETE - permanently removes records).
    Enforce ownership: only SUPER_ADMIN may delete arbitrary jobs; other
    roles may only delete jobs they created. If any requested IDs are not owned by the current user,
    return 403 listing the offending IDs.
    """
    try:
        async for db in get_db():
            # Extract authenticated user from request state (middleware places user here)
            request_user = getattr(request, "state", None)
            current_user = getattr(request_user, "user", None) if request_user else None

            # If no user info is present, reject
            if not current_user:
                return ResponseBuilder.error(
                    message="Unauthorized: User information missing.",
                    errors=["User authentication required."],
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # SUPER_ADMIN can delete any jobs
            user_role = None
            if isinstance(current_user, dict):
                user_role = current_user.get("role")

            if user_role != "SUPER_ADMIN":
                # For non-super users, ensure they only operate on their own jobs
                reader = JobPostReader(db)
                unauthorized_ids = []
                invalid_ids = []
                for jid in job_ids:
                    try:
                        job_candidate = reader.get_job(job_id=jid)
                        job_payload = await job_candidate if inspect.isawaitable(job_candidate) else job_candidate
                    except Exception:
                        job_payload = None

                    if not job_payload:
                        # treat missing/invalid job id as invalid
                        invalid_ids.append(jid)
                        continue

                    creator_id = job_payload.get("user_id") or job_payload.get("created_by_user_id")
                    # Current user id may be under different keys (user_id or sub)
                    cur_uid = None
                    if isinstance(current_user, dict):
                        cur_uid = current_user.get("user_id") or current_user.get("sub")

                    if creator_id != cur_uid:
                        unauthorized_ids.append(jid)

                if invalid_ids:
                    return ResponseBuilder.error(
                        message="One or more provided job IDs are invalid or not found.",
                        errors={"invalid_job_ids": invalid_ids},
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                if unauthorized_ids:
                    return ResponseBuilder.error(
                        message="You don't have permission to delete one or more job posts in this batch.",
                        errors={"unauthorized_job_ids": unauthorized_ids},
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

            # At this point permissions are satisfied — prefer service-layer batch delete if present
            update_service = UpdateJobPost(db)
            try:
                batch_candidate = update_service.delete_jobs_batch(job_ids)
                batch_result = await batch_candidate if inspect.isawaitable(batch_candidate) else batch_candidate
            except Exception:
                batch_result = None

            if isinstance(batch_result, dict) and batch_result.get("success") is not None:
                return batch_result

            # Permanently delete jobs using hard delete
            affected = await hard_delete_jobs_batch(db, job_ids)
            if not affected:
                return ResponseBuilder.error(message="No valid job IDs provided or none deleted", status_code=400)
            return ResponseBuilder.success(
                message=f"Successfully deleted {affected} job post(s) and all related records.", 
                data={"rows_affected": affected}
            )
    except Exception as e:
        logger.error(f"Error batch deleting jobs: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"Failed to delete jobs: {e}")


async def candidate_stats_controller(job_id: str) -> StandardResponse:
    """Return aggregated candidate counts for a job. If profile counters not available, return zeros."""
    # OPTIMIZED: Validate UUID early
    try:
        _uuid.UUID(job_id)
    except ValueError:
        return ResponseBuilder.error(
            message="Invalid job ID format. Must be a valid UUID.", 
            errors=["Invalid job ID format. Must be a valid UUID."], 
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        async for db in get_db():
            from app.db.repository.profile_repository import ProfileRepository
            repo = ProfileRepository(db)
            applied = await repo.count_by_status(job_id, status="applied")
            shortlisted = await repo.count_by_status(job_id, status="shortlisted")
            rejected = await repo.count_by_status(job_id, status="rejected")
            under_review = await repo.count_by_status(job_id, status="under_review")
            data = {
                "profile_counts": {
                    "applied": applied,
                    "shortlisted": shortlisted,
                    "rejected": rejected,
                    "under_review": under_review,
                }
            }
            return ResponseBuilder.success(message="Fetched candidate stats.", data=data)
    except Exception as e:
        logger.error(f"Error getting candidate stats: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"Failed to fetch candidate stats: {e}")

# ------------------------------------------------------------------
# --- NEW: PUBLIC SEARCH CONTROLLER ---
# ------------------------------------------------------------------
async def search_public_jobs_controller(
    search_service: PublicSearchService = Depends(get_public_search_service),
    role: Optional[str] = Query(None, description="Job title/role query"),
    skills: Optional[str] = Query(None, description="Comma-separated list of skills"),
    locations: Optional[str] = Query(None, description="Comma-separated list of locations")
) -> StandardResponse:
    """
    Public endpoint to search for active jobs with weighted ranking.
    """
    try:
        # Convert comma-separated strings to lists
        skills_list = [s.strip() for s in skills.split(',')] if skills else []
        locations_list = [l.strip() for l in locations.split(',')] if locations else []

        # At least one search parameter must be provided
        if not role and not skills_list and not locations_list:
            return ResponseBuilder.error(
                message="Please provide at least one search criteria (role, skills, or locations).",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        jobs = await search_service.search_jobs(
            search_role=role,
            search_skills=skills_list,
            search_locations=locations_list
        )
        
        return ResponseBuilder.success(
            message=f"Found {len(jobs)} matching jobs.",
            data={"jobs": jobs}
        )
    except Exception as e:
        logger.error(f"Error searching public jobs: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"An unexpected error occurred during search: {e}")

# ------------------------------------------------------------------
# --- NEW: SEARCH SUGGESTIONS CONTROLLER ---
# ------------------------------------------------------------------
async def get_search_suggestions_controller(
    search_service: PublicSearchService = Depends(get_public_search_service)
) -> StandardResponse:
    """
    Public endpoint to get autocomplete suggestions for search boxes.
    """
    try:
        suggestions = await search_service.get_suggestions()
        return ResponseBuilder.success(
            message="Fetched search suggestions.",
            data=suggestions
        )
    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}", exc_info=True)
        return ResponseBuilder.server_error(f"Failed to fetch suggestions: {e}")





















