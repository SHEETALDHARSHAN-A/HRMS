# app/services/admin_service/invite_admin_service.py

import json
import uuid
import logging
import redis.asyncio as redis

from hashlib import sha256
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.schemas.authentication_request import AdminInviteRequest
from app.db.models.invitation_model import Invitation, InvitationStatus
from app.db.repository.authentication_repository import check_user_existence

from app.utils.email_utils import send_admin_invite_email
from app.utils.standard_response_utils import ResponseBuilder

settings = AppConfig()

class InviteAdminService:
    def __init__(self, db: AsyncSession, cache: redis.Redis):
        self.db = db
        self.cache = cache
        self.token_expire_seconds = settings.otp_expire_seconds 
        self.FRONTEND_BASE_URL = settings.frontend_base_url
        self.logger = logging.getLogger(__name__)

    def create_invite_token(self) -> str:
        """Generates a secure, non-JWT token for the single-use link."""
        return str(uuid.uuid4())

    async def generate_admin_invite(self, input: AdminInviteRequest, invited_by_user_id: str):

        email = input.email

        if await check_user_existence(self.db, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists."
            )
        
        invite_token = self.create_invite_token()
        
        # Compute token expiry seconds. Allow override from request (expiration_days)
        token_expire_seconds = self.token_expire_seconds
        if getattr(input, 'expiration_days', None):
            try:
                days = int(input.expiration_days)
                if days > 0:
                    token_expire_seconds = days * 24 * 60 * 60
            except Exception:
                pass

        # Create database record for invitation tracking
        expires_at = datetime.utcnow() + timedelta(seconds=token_expire_seconds)
        invitation_record = Invitation(
            invited_by=invited_by_user_id,
            invited_email=email,
            invited_first_name=input.first_name,
            invited_last_name=input.last_name,
            invited_phone_number=input.phone_number,
            invited_role=input.role,
            status=InvitationStatus.PENDING.value,
            invitation_token=sha256(invite_token.encode()).hexdigest(),  # Store hashed token
            expires_at=expires_at
        )
        
        try:
            self.db.add(invitation_record)
            await self.db.commit()
            await self.db.refresh(invitation_record)
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create invitation record."
            )
        
        redis_data = {
            "mode_of_login": "admin_invite",
            "role": input.role,  # Store the role (SUPER_ADMIN, ADMIN, HR)
            "first_name": input.first_name,
            "last_name": input.last_name,
            "email": input.email,
            "phone_number": input.phone_number,
            "token": invite_token,
            "invitation_id": str(invitation_record.invitation_id)  # Add invitation ID for tracking
        }
        
        try:
            cache_key = f'admin_invite:{invite_token}'

            # Ensure TTL is a positive integer (seconds)
            try:
                token_expire_seconds = int(token_expire_seconds)
            except Exception:
                token_expire_seconds = int(self.token_expire_seconds)

            if token_expire_seconds <= 0:
                token_expire_seconds = int(self.token_expire_seconds)

            # Store in Redis with explicit TTL (seconds). Using ex ensures the key lives for the full requested duration.
            await self.cache.set(cache_key, json.dumps(redis_data), ex=token_expire_seconds)

            # Verify TTL was set (debug logging). ttl() returns remaining seconds or -1 if no TTL.
            try:
                remaining = await self.cache.ttl(cache_key)
                self.logger.info(f"Stored invite cache key={cache_key} with TTL={token_expire_seconds}s (redis reports: {remaining}s)")
            except Exception:
                # Non-fatal: continue even if ttl check fails
                self.logger.debug(f"Stored invite cache key={cache_key}; could not verify TTL via redis.ttl()")

        except Exception as e:
            # Rollback database record if Redis fails
            await self.db.delete(invitation_record)
            await self.db.commit()
            self.logger.error(f"Failed to store invitation token in redis: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store invitation token.")

        invite_link = f"{self.FRONTEND_BASE_URL}/auth/complete-admin-setup?token={invite_token}"
        admin_name = f"{input.first_name} {input.last_name if input.last_name else ''}".strip()
        
        # Pass DB session so the email sender can lookup and use any saved templates
        if not await send_admin_invite_email(email, admin_name, invite_link, invitation_record.expires_at, db=self.db):
            # Clean up both Redis and database on email failure
            await self.cache.delete(cache_key)
            await self.db.delete(invitation_record)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to send Admin invitation email"
            )

        # Human-friendly expires_in (in days if >1, otherwise in minutes)
        if token_expire_seconds >= 86400 and token_expire_seconds % 86400 == 0:
            expires_in_val = f"{token_expire_seconds//86400} days"
        elif token_expire_seconds >= 3600 and token_expire_seconds % 3600 == 0:
            expires_in_val = f"{token_expire_seconds//3600} hours"
        else:
            expires_in_val = f"{token_expire_seconds//60} minutes"

        return ResponseBuilder.success(
            "Admin invitation link sent successfully",
            {
                "expires_in": expires_in_val,
                "invitation_id": str(invitation_record.invitation_id),
                "expires_at": invitation_record.expires_at.isoformat()
            },
            status_code=status.HTTP_200_OK
        )