# app/controllers/resume_controller.py

import logging
import inspect
from typing import List, Dict, Any
from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.standard_response import StandardResponse
from app.services.resume.resume_service import ResumeService
from app.utils.standard_response_utils import ResponseBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def handle_resume_upload(
    job_id: str,
    files: List[UploadFile],
    form_metadata: Dict[str, Any] = None,
    db: AsyncSession = None,
) -> Dict[str, Any]:
    """Compatibility wrapper expected by other controllers.
    Calls the internal ResumeService.process_resume_upload and returns its result.
    Accepts optional form_metadata (from forms) and attaches it to the response for callers that expect it.
    """
    service = ResumeService(db)
    try:
        # Pass through any provided form metadata and DB session so the service
        # can create initial Profile records from the form prior to resume extraction.
        maybe_result = service.process_resume_upload(
            job_id, files, form_metadata=form_metadata, db=db
        )
        if inspect.isawaitable(maybe_result):
            result = await maybe_result
        else:
            result = maybe_result

        # Attach form metadata when provided so callers can log/store it if needed
        if form_metadata and isinstance(result, dict):
            result.setdefault("form_metadata", form_metadata)

        return result
    except Exception as e:
        logger.exception(f"[ResumeController] Error in handle_resume_upload: {e}")
        return {
            "status": "failure",
            "saved_count": 0,
            "skipped_files": [f["filename"] for f in files] if files else [],
            "message": str(e),
        }


async def upload_resumes_controller(job_id: str, files: List[UploadFile], db: AsyncSession) -> Dict[str, Any]:
    """Controller for handling resume uploads with partial success and specific feedback."""
    try:
        service = ResumeService(db)
        # Service returns a dictionary with detailed status
        maybe_result = service.process_resume_upload(job_id, files)
        if inspect.isawaitable(maybe_result):
            result = await maybe_result
        else:
            result = maybe_result

        status_flag = result['status']
        saved_count = result['saved_count']
        skipped_files = result['skipped_files']
        
        # --- Constructing the Response Message & Status ---

        # 1. Base message for valid files
        if saved_count > 0:
            # Full or Partial Success
            success_message = f"{saved_count} resume(s) uploaded successfully and submitted for processing."
            final_status_code = status.HTTP_202_ACCEPTED
        else:
            # Full Failure (either validation or job ID not found)
            success_message = "" 
            final_status_code = status.HTTP_400_BAD_REQUEST # Defaulting to 400 for client issues

        # 2. Append skipped file details if needed
        if skipped_files:
            skipped_list_str = ", ".join(skipped_files)
            
            if saved_count > 0:
                # Partial Success: Use 202
                final_message = f"{success_message} Note: {len(skipped_files)} file(s) were skipped (invalid format/empty): {skipped_list_str}"
            else:
                # Complete Validation Failure: Use 400
                final_message = f"Upload failed. {len(files)} file(s) were provided, but all were skipped due to format issues: {skipped_list_str}. Only PDF and DOCX formats are accepted."
                
        else:
            # Full Success or full failure related to Job ID/Internal Error
            final_message = success_message if saved_count > 0 else result['message']


        # --- Returning the Final Response ---

        if status_flag == 'success' or saved_count > 0:
            # Return 202 (Partial or Full Success)
            # Include optional task_id and saved_files when provided by the service
            data_payload = {
                "saved_count": saved_count,
                "skipped_files": skipped_files
            }
            if isinstance(result, dict) and result.get('task_id'):
                data_payload['task_id'] = result.get('task_id')
            if isinstance(result, dict) and result.get('saved_files'):
                data_payload['saved_files'] = result.get('saved_files')

            return ResponseBuilder.success(
                message=final_message,
                status_code=final_status_code,
                data=data_payload
            )
        elif status_flag == 'validation_failure' or final_status_code == status.HTTP_400_BAD_REQUEST:
             # Return 400 for client-side issues (invalid files, job not found)
            return ResponseBuilder.error(
                message=final_message,
                errors=[final_message],
                status_code=status.HTTP_400_BAD_REQUEST
            )
        else:
            # Default to 500 for unexpected internal errors
            return ResponseBuilder.server_error(
                message=final_message or "Unexpected internal server error."
            )

    except Exception as e:
        logger.exception(f"[ResumeController] Unexpected error during upload: {e}")
        return ResponseBuilder.server_error(
            message=f"Unexpected internal server error: {str(e)}"
        )