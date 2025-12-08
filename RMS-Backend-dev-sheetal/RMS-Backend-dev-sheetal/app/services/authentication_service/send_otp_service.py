# app/services/authentication_service/send_otp_serivce.py

import json
import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_model import User
from app.config.app_config import AppConfig
from app.schemas.authentication_request import SendOTPRequest
from app.db.repository.authentication_repository import check_user_existence

from app.utils.email_utils import send_otp_email
from app.utils.authentication_utils import generate_otp_code
from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_helpers import validate_input_email

settings = AppConfig()

class SendOtpService:
    def __init__(self, db: AsyncSession, cache: redis.Redis):
        self.db = db
        self.cache = cache
        self.otp_expire_seconds = settings.otp_expire_seconds

    async def send_otp(self, input: SendOTPRequest):
  
        email = input.email
        validate_input_email(email)

        user: User = await check_user_existence(self.db, email)
        if not user or not user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have not registered yet"
            )

        otp = generate_otp_code()
        redis_data = {
            "mode_of_login": "sign_in",
            "email": email, 
            "otp": otp,
            "role": user.role  # Store role instead of user_type
        }
        
        try:
            cache_key = f'otp:{email}'
            await self.cache.hset(cache_key, email, json.dumps(redis_data))
            await self.cache.expire(cache_key, self.otp_expire_seconds)
            
        except Exception as e:
            print(f"[ERROR] Failed to store OTP in Redis: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store OTP.")
        
        if not await send_otp_email(email, otp, subject="Smart HR Agent - Login OTP", db=self.db):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP email")

        remember_me_expire_days = settings.remember_me_expire_days
        return ResponseBuilder.success(
            "OTP sent successfully",
            {
                "expires_in": f"{self.otp_expire_seconds//60} minutes",
                "remember_me_expire_days": remember_me_expire_days
            },
            status_code=status.HTTP_200_OK
        )