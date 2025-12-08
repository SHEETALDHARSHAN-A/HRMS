# app/api/v1/career_routes.py

import json
import logging
import redis.asyncio as redis

from fastapi import APIRouter, Body, Depends, Request, status, UploadFile

from app.db.connection_manager import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis_manager import get_redis_client
from app.utils.standard_response_utils import ResponseBuilder
from app.controllers.career_controller import (
    handle_send_career_otp_controller,
    handle_verify_and_submit_controller,
)

career_router = APIRouter(prefix="/career", tags=["Career"])

@career_router.post("/apply/send-otp", response_model=None, summary="Send OTP for career application (public)")
async def career_send_otp(
    payload: dict = Body(...),
    cache: redis.Redis = Depends(get_redis_client),
):
    """Route wrapper that delegates to the career controller."""
    return await handle_send_career_otp_controller(payload, cache)


@career_router.post("/apply/verify-and-submit", response_model=None, summary="Verify OTP and submit application")
async def career_verify_and_submit(
    request: Request,
    cache: redis.Redis = Depends(get_redis_client),
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP and submit career application with optional resume files."""
    from fastapi import File, UploadFile
    
    # Parse multipart form data
    form_data = await request.form()
    
    # Debug: log form data keys
    logging.info(f"[CAREER APP] Form data keys: {list(form_data.keys())}")
    
    # Extract required fields
    job_id = form_data.get("jobId") or form_data.get("job_id")
    email = form_data.get("email")
    otp = form_data.get("otp")
    
    # Extract optional application data
    first_name = form_data.get("firstName") or form_data.get("first_name")
    last_name = form_data.get("lastName") or form_data.get("last_name") 
    phone = form_data.get("phone")
    cover_letter = form_data.get("coverLetter") or form_data.get("cover_letter")
    
    # Debug: log extracted values
    logging.info(f"[CAREER APP] Extracted - Name: {first_name} {last_name}, Email: {email}, Phone: {phone}")
    
    # Extract resume files
    files = []
    for key, value in form_data.items():
        if (key == "resume" or key.startswith("resume")) and hasattr(value, 'filename'):
            files.append(value)
    
    # Prepare application data
    email_prefix = email.split('@')[0] if email and '@' in email else 'unknown'
    application_data = {
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "cover_letter": cover_letter,
        "application_id": f"app_{job_id}_{email_prefix}"  # Generate a temp ID
    }
    
    return await handle_verify_and_submit_controller(
        job_id=job_id,
        email=email,
        otp=otp,
        files=files,
        application_data=application_data,
        cache=cache,
        db=db,
    )
