# app/services/authentication_service/verify_otp_service.py

import json
import redis.asyncio as redis
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Response

from app.db.models.user_model import User
from app.db.repository.authentication_repository import check_user_existence, create_user_from_cache

from app.config.app_config import AppConfig
from app.schemas.authentication_request import VerifyOTPRequest

from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_helpers import validate_input_email
from app.utils.authentication_utils import create_access_token, create_refresh_token, get_jti_from_token 

settings = AppConfig()

class VerifyOtpService:
    def __init__(self, db: AsyncSession, cache: redis.Redis):
        self.db = db
        self.cache = cache
        self.access_token_expire_min = settings.access_token_expire_minutes
        self.access_refresh_token_expire_hrs = settings.access_refresh_token_expire_hours
        self.samesite = settings.samesite
        self.secure = settings.secure

    async def verify_otp(self, input: VerifyOTPRequest, response: Response):
        email = input.email
        validate_input_email(email)
        
        cache_key = f'otp:{email}'
        otp_data = await self.cache.hget(cache_key, email)
        
        if otp_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OTP not found or expired.")

        otp_info = json.loads(otp_data)

        if otp_info.get("otp") != input.otp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        mode_of_login = otp_info.get('mode_of_login')
        is_sign_up = mode_of_login == "sign_up"

        user: User | None = None
        
        if is_sign_up:
            if await check_user_existence(self.db, email):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
                
            user = await create_user_from_cache(self.db, otp_info)
            if user:
                _ = user.first_name 
                _ = user.last_name            
        else:
            user = await check_user_existence(self.db, email)
        
        if not user:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found after OTP verification.")
            
        await self.cache.hdel(cache_key, email)

        user_id = str(user.user_id)
        user_role = user.role  # Get the role (SUPER_ADMIN, ADMIN, HR, CANDIDATE)

        # Generate tokens using role
        access_token = create_access_token(user_id, user_role, first_name=user.first_name, last_name=user.last_name)
        refresh_token = create_refresh_token(user_id, user_role)
        
        # --- Store active refresh JTI in a per-user Redis SET so we can revoke ALL sessions when needed ---
        refresh_jti = get_jti_from_token(refresh_token)
        if refresh_jti:
            # Key: active_refresh_jtis:{user_id} (a Redis set of JTIs)
            refresh_expiry_seconds = int(timedelta(hours=self.access_refresh_token_expire_hrs).total_seconds())
            active_jtis_key = f"active_refresh_jtis:{user_id}"
            # Add the JTI to the set and set the TTL on the set to match the refresh token expiry
            await self.cache.sadd(active_jtis_key, refresh_jti)
            await self.cache.expire(active_jtis_key, refresh_expiry_seconds)
        # Also track the access token JTI so we can force-invalidate active access tokens immediately when needed
        access_jti = get_jti_from_token(access_token)
        if access_jti:
            access_expiry_seconds = int(timedelta(minutes=self.access_token_expire_min).total_seconds())
            active_access_key = f"active_access_jtis:{user_id}"
            await self.cache.sadd(active_access_key, access_jti)
            await self.cache.expire(active_access_key, access_expiry_seconds)
        # ------------------------------------------------------------------------------------

        access_max_age = int(timedelta(minutes=self.access_token_expire_min).total_seconds())
        refresh_max_age = int(timedelta(hours=self.access_refresh_token_expire_hrs).total_seconds())

        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=access_max_age, samesite=self.samesite, secure=self.secure, path="/")
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=refresh_max_age, samesite=self.samesite, secure=self.secure, path="/")

        data = {
            "user_id": user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user_role,  # Return role (SUPER_ADMIN, ADMIN, HR, CANDIDATE)
            "message": "OTP verified successfully",
            "token": access_token
        }

        return ResponseBuilder.success("OTP verified successfully", data)