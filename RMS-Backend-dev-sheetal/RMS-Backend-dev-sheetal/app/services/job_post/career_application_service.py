# app/services/job_post/career_application_services.py

import json
import logging
import redis.asyncio as redis

from fastapi import status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.db.models.resume_model import Profile
from app.utils.email_utils import send_otp_email
from app.db.connection_manager import AsyncSessionLocal
from app.utils.authentication_utils import generate_otp_code
from app.utils.standard_response_utils import ResponseBuilder

logger = logging.getLogger(__name__)
settings = AppConfig()

class CareerApplicationService:
    """Service handling career application OTP send/verify logic.

    This service is intentionally minimal for now: it generates an OTP,
    stores it in Redis under a job-scoped key, sends the OTP email, and
    returns a ResponseBuilder-shaped dict.
    """

    def __init__(self, cache: redis.Redis):
        self.cache = cache

    async def send_otp(self, job_id: str, email: str, meta: dict | None = None) -> dict:
        # --- PRE-CHECK: If this email has already applied for this job, do not send OTP ---
        try:
            async with AsyncSessionLocal() as db:
                try:
                    q = await db.execute(
                        select(Profile).where(Profile.job_id == job_id, Profile.email == email)
                    )
                    existing = q.scalars().first()
                    if existing:
                        logger.info("Duplicate application detected when sending OTP for job %s by %s", job_id, email)
                        return ResponseBuilder.error(
                            "You have already applied for this job.",
                            ["already_applied"],
                            status_code=status.HTTP_409_CONFLICT,
                        )
                except Exception as e:
                    logger.exception("Error checking existing profile before sending OTP: %s", e)
        except Exception as e:
            # If DB initialization or connection fails, log but continue to OTP flow —
            # we don't want DB errors to silently prevent applicants from applying.
            logger.warning("Could not perform duplicate check before sending OTP: %s", e)

        otp = generate_otp_code()
        cache_key = f"otp:career:{job_id}:{email}"
        redis_data = {
            "mode": "career_application",
            "job_id": job_id,
            "email": email,
            "otp": otp,
        }
        if meta:
            redis_data.update(meta)

        try:
            await self.cache.hset(cache_key, email, json.dumps(redis_data))
            await self.cache.expire(cache_key, settings.otp_expire_seconds)
        except Exception as e:
            logger.exception("Failed to store career OTP in Redis: %s", e)
            return ResponseBuilder.error("Failed to store OTP", [str(e)], status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            subject = f"Your application OTP"
            # Use a DB session so saved OTP templates (if any) are used for career application OTPs
            async with AsyncSessionLocal() as db:
                sent = await send_otp_email(email, otp, subject, db=db)
            if not sent:
                logger.error("send_otp_email returned False for %s", email)
                return ResponseBuilder.error("Failed to send OTP email", ["smtp failure"], status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception("Error sending career OTP email: %s", e)
            return ResponseBuilder.error("Failed to send OTP email", [str(e)], status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return ResponseBuilder.success(
            "OTP sent successfully",
            {"expires_in": f"{settings.otp_expire_seconds//60} minutes"},
            status_code=status.HTTP_200_OK,
        )

    async def verify_otp_and_submit_application(
        self, 
        job_id: str, 
        email: str, 
        otp: str, 
        application_data: dict,
        db: AsyncSession | None = None,
    ) -> dict:
        """Verify OTP and submit career application with resume processing."""
        cache_key = f"otp:career:{job_id}:{email}"
        
        try:
            # Get stored OTP data
            stored_data_raw = await self.cache.hget(cache_key, email)
            if not stored_data_raw:
                logger.warning("No OTP found for job %s email %s", job_id, email)
                return ResponseBuilder.error(
                    "Invalid or expired OTP", 
                    ["OTP not found or expired"], 
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            stored_data = json.loads(stored_data_raw)
            stored_otp = stored_data.get("otp")
            
            if stored_otp != otp:
                logger.warning("Invalid OTP for job %s email %s", job_id, email)
                return ResponseBuilder.error(
                    "Invalid OTP", 
                    ["OTP does not match"], 
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # OTP is valid. Before proceeding, check DB for duplicate application
            try:
                if db is not None:
                    q = await db.execute(
                        select(Profile).where(Profile.job_id == job_id, Profile.email == email)
                    )
                    existing = q.scalars().first()
                    if existing:
                        logger.info("Duplicate application attempt for job %s by %s", job_id, email)
                        return ResponseBuilder.error(
                            "You have already applied for this job.",
                            ["already_applied"],
                            status_code=status.HTTP_409_CONFLICT,
                        )
            except Exception as e:
                logger.exception("Error checking existing profile for duplicate application: %s", e)

            # Delete OTP from cache now that we validated it
            await self.cache.delete(cache_key)
            
            # Here you would typically:
            # 1. Save application data to database
            # 2. Process the resume files if any
            # 3. Send confirmation emails
            # 4. Trigger any background processing
            
            logger.info("Career application submitted successfully for job %s by %s", job_id, email)
            
            return ResponseBuilder.success(
                "Application submitted successfully",
                {
                    "job_id": job_id,
                    "email": email,
                    "application_id": application_data.get("application_id", "pending")
                },
                status_code=status.HTTP_200_OK,
            )
            
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in stored OTP data: %s", e)
            return ResponseBuilder.error(
                "Invalid stored data", 
                ["Corrupted OTP data"], 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.exception("Error verifying OTP and submitting application: %s", e)
            return ResponseBuilder.error(
                "Failed to submit application", 
                [str(e)], 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
