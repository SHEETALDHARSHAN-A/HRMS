# app/controllers/career_controller.py

import logging
import redis.asyncio as redis

from fastapi import status
from fastapi.responses import JSONResponse

from app.utils.standard_response_utils import ResponseBuilder
from app.services.job_post.career_application_service import CareerApplicationService

logger = logging.getLogger(__name__)


async def handle_send_career_otp_controller(payload: dict, cache: redis.Redis) -> JSONResponse:
    """Controller that validates request payload and delegates to the service."""
    job_id = payload.get("jobId") or payload.get("job_id")
    email = payload.get("email")

    if not job_id or not email:
        return JSONResponse(content=ResponseBuilder.error("Missing required fields: 'jobId' and 'email' are required", ["jobId and email are required"], status_code=status.HTTP_400_BAD_REQUEST), status_code=status.HTTP_400_BAD_REQUEST)

    meta = {
        "first_name": payload.get("firstName") or payload.get("first_name"),
        "last_name": payload.get("lastName") or payload.get("last_name"),
        "phone": payload.get("phone"),
    }

    service = CareerApplicationService(cache)
    result = await service.send_otp(job_id=job_id, email=email, meta=meta)

    # service returns a ResponseBuilder-shaped dict
    return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))


async def handle_verify_and_submit_controller(
    job_id: str,
    email: str, 
    otp: str,
    files: list,
    application_data: dict,
    cache: redis.Redis,
    db = None,
) -> JSONResponse:
    """Controller that handles OTP verification and application submission."""
    
    if not job_id or not email or not otp:
        return JSONResponse(
            content=ResponseBuilder.error(
                "Missing required fields", 
                ["jobId, email, and otp are required"], 
                status_code=status.HTTP_400_BAD_REQUEST
            ), 
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    service = CareerApplicationService(cache)
    
    # First verify OTP and submit application data
    result = await service.verify_otp_and_submit_application(
        job_id=job_id,
        email=email, 
        otp=otp,
        application_data=application_data,
        db=db,
    )
    
    # If OTP verification failed, return error
    if not result.get("success"):
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_400_BAD_REQUEST))
    
    # If there are resume files, process them with form data
    if files:
        try:
            from app.controllers.resume_controller import handle_resume_upload
            # Pass the form data so the upload service can use it for profile creation
            form_metadata = {
                "source": "career_application",
                "applicant_name": f"{application_data.get('first_name', '')} {application_data.get('last_name', '')}".strip(),
                "applicant_email": email,
                "applicant_phone": application_data.get('phone', ''),
            }
            logger.info(f"[CAREER APP] Constructed form_metadata: {form_metadata}")
            # Pass the DB session through so resume upload repository calls have a valid session
            upload_result = await handle_resume_upload(job_id, files, form_metadata, db=db)
            result["data"]["resume_processing"] = upload_result
            logger.info("Resume files uploaded and queued for processing: %s", upload_result.get("task_id"))
        except Exception as e:
            logger.exception("Failed to process resume files: %s", e)
            # Don't fail the entire application, just log the error
            result["data"]["resume_processing"] = {"error": str(e)}
    
    return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
