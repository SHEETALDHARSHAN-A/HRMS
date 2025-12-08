# app/services/admin_service/complete_admin_setup_service.py

import json
import logging

from hashlib import sha256
import redis.asyncio as redis
from datetime import timedelta, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Response

from app.db.models.user_model import User
from app.db.models.invitation_model import Invitation, InvitationStatus
from app.db.models.notification_model import Notification, NotificationType

from app.config.app_config import AppConfig
from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_utils import create_access_token, create_refresh_token
from app.db.repository.authentication_repository import create_user_from_cache, check_user_existence

settings = AppConfig()

class CompleteAdminSetupService:
    def __init__(self, db: AsyncSession, cache: redis.Redis):
        self.db = db
        self.cache = cache
        # 💡 NEW: Token settings from AppConfig
        self.access_token_expire_min = settings.access_token_expire_minutes
        self.access_refresh_token_expire_hrs = settings.access_refresh_token_expire_hours
        self.samesite = settings.samesite
        self.secure = settings.secure

    async def complete_admin_setup(self, token: str, response: Response): # 💡 ADD response
        cache_key = f'admin_invite:{token}'

        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data is None:
                logging.warning(f"[Redis] No data found for key: {cache_key}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation link expired or invalid."
                )

            invite_info = json.loads(cached_data)
            email = invite_info.get("email")
            invited_role = invite_info.get("role")

            # Validate invitation data - must have mode and valid role
            if invite_info.get("mode_of_login") != "admin_invite" or not invited_role or invited_role not in ["SUPER_ADMIN", "ADMIN", "HR"]:
                logging.error(f"[Redis] Invalid invitation data for key: {cache_key}")
                await self.cache.delete(cache_key)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid invitation data."
                )

            if await check_user_existence(self.db, email):
                logging.info(f"[PostgreSQL] Admin account already exists for email: {email}")
                await self.cache.delete(cache_key)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Admin account already registered. Please log in."
                )

            try:
                new_admin: User = await create_user_from_cache(self.db, invite_info)
            except Exception as e:
                logging.error(f"[PostgreSQL] Failed to create admin in DB: {e}")
                await self.cache.delete(cache_key)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to finalize account creation due to database error: {e}"
                )

            await self.cache.delete(cache_key)
            logging.info(f"[Redis] Successfully deleted cache key: {cache_key}")

            # Update invitation status and create notification
            try:
                await self._update_invitation_and_notify(token, new_admin.user_id, invite_info)
            except Exception as e:
                logging.warning(f"Failed to update invitation status or create notification: {e}")
            return ResponseBuilder.success(
                "Admin account created successfully. Please sign in to continue.",
                {
                    "email": new_admin.email, 
                    "first_name": new_admin.first_name,
                    "last_name": new_admin.last_name,
                    "account_created": True,
                    "redirect_to_signin": True
                },
                status_code=status.HTTP_201_CREATED
            )
            # --------------------------------------------------------------

        except HTTPException as http_exc:
            await self.cache.delete(cache_key)
            raise http_exc

        except Exception as e:
            # Catch-all for unexpected errors
            logging.error(f"[Service] Unexpected error during admin setup: {e}")
            await self.cache.delete(cache_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during admin setup."
            )
    
    async def _update_invitation_and_notify(self, token: str, accepted_user_id: str, invite_info: dict):
        """Update invitation status and create notification for inviter."""
        try:
            # Find the invitation record using the hashed token
            token_hash = sha256(token.encode()).hexdigest()
            
            invitation_query = select(Invitation).where(
                Invitation.invitation_token == token_hash,
                Invitation.status == InvitationStatus.PENDING.value
            )
            result = await self.db.execute(invitation_query)
            invitation = result.scalar_one_or_none()
            
            if invitation:
                # Update invitation status
                invitation.status = InvitationStatus.ACCEPTED.value
                invitation.accepted_user_id = accepted_user_id
                invitation.accepted_at = datetime.utcnow()
                
                # Create notification for the person who sent the invitation
                notification = Notification(
                    user_id=invitation.invited_by,
                    type=NotificationType.INVITATION_ACCEPTED.value,
                    title="Invitation Accepted",
                    message=f"{invite_info.get('first_name', 'Someone')} {invite_info.get('last_name', '')} has accepted your admin invitation and created their account.",
                    related_invitation_id=invitation.invitation_id,
                    related_user_id=accepted_user_id
                )
                
                self.db.add(notification)
                await self.db.commit()
                logging.info(f"Updated invitation {invitation.invitation_id} and created notification")
            else:
                logging.warning(f"No pending invitation found for token hash")
                
        except Exception as e:
            logging.error(f"Error updating invitation status: {e}")
            await self.db.rollback()
            raise