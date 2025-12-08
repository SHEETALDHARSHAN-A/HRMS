# app/services/authentication_service/resend_otp_serivce.py

import json
import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.schemas.authentication_request import SendOTPRequest

from app.utils.email_utils import send_otp_email
from app.utils.authentication_utils import generate_otp_code
from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_helpers import validate_input_email

settings = AppConfig()

class ResendOtpService:
    def __init__(self, cache: redis.Redis, db: AsyncSession | None = None):
        # Accept an optional DB session so the resend flow can render saved templates
        self.cache = cache
        self.db = db
        self.otp_expire_seconds = settings.otp_expire_seconds

    async def resend_otp(self, input: SendOTPRequest):

        email = input.email
        validate_input_email(email)
        cache_key = f'otp:{email}'

        existing_otp_data = await self.cache.hget(cache_key, email)
        
        if existing_otp_data is None:
            # No active OTP, create a new session
            new_otp = generate_otp_code()
            redis_data = {"otp": new_otp}
            await self.cache.hset(cache_key, email, json.dumps(redis_data))
            await self.cache.expire(cache_key, self.otp_expire_seconds)
            subject = "Smart HR Agent - OTP Resent"
            if not await send_otp_email(email, new_otp, subject=subject, db=self.db):
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP email")
            return ResponseBuilder.success(
                "OTP sent successfully",
                {"expires_in": f"{self.otp_expire_seconds//60} minutes"},
                status_code=status.HTTP_200_OK
            )
        
        new_otp = generate_otp_code()
        redis_data = json.loads(existing_otp_data)
        
        redis_data["otp"] = new_otp 
        
        try:
            await self.cache.hset(cache_key, email, json.dumps(redis_data))
            await self.cache.expire(cache_key, self.otp_expire_seconds)
            
        except Exception as e:
            print(f"[ERROR] Failed to update OTP in Redis: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to resend OTP.")
        
        subject = "Smart HR Agent - OTP Resent"
        if not await send_otp_email(email, new_otp, subject=subject, db=self.db):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP email")

        return ResponseBuilder.success(
            "OTP sent successfully",
            {"expires_in": f"{self.otp_expire_seconds//60} minutes"},
            status_code=status.HTTP_200_OK
        )