# app/services/admin_service/update_admin_service.py

import json
import logging
import redis.asyncio as redis

from uuid import UUID, uuid4
from urllib.parse import quote_plus
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from app.config.app_config import AppConfig
from app.db.repository.user_repository import get_user_by_id, update_user_details
from app.schemas.authentication_request import AdminUpdateRequest, UpdateEmailVerifyTokenRequest

from app.utils.standard_response_utils import ResponseBuilder
import app.utils.email_utils as email_utils
from app.utils.authentication_utils import generate_token, add_jti_to_blocklist 

logger = logging.getLogger(__name__)

settings = AppConfig()

# Re-export commonly-used email helper names at module level so tests that
# monkeypatch these names on this module continue to work. These are simple
# aliases to the implementations in app.utils.email_utils and will reflect
# changes whether tests patch this module or the original email_utils module.
send_email_change_transfer_notification = email_utils.send_email_change_transfer_notification
send_name_update_verification_link = email_utils.send_name_update_verification_link
send_name_update_success_notification = email_utils.send_name_update_success_notification
send_phone_update_verification_link = email_utils.send_phone_update_verification_link
async def send_email_update_verification_link(*args, **kwargs):
    # Resolve the implementation at call time so tests that patch
    # `app.utils.email_utils.send_email_update_verification_link` are effective.
    return await email_utils.send_email_update_verification_link(*args, **kwargs)
send_admin_role_change_email = email_utils.send_admin_role_change_email
send_otp_email = email_utils.send_otp_email
send_otp_for_email_update = email_utils.send_otp_for_email_update
send_admin_invite_email = email_utils.send_admin_invite_email
send_admin_removal_email = email_utils.send_admin_removal_email

class UpdateAdminService:
    def __init__(self, db: AsyncSession, cache: redis.Redis):
        self.db = db
        self.cache = cache
        self.BASE_FRONTEND_URL = settings.frontend_url
        self.API_URL = settings.get_api_url
        self.VERIFY_KEY_PREFIX = "verify_update:"
        self.LINK_EXPIRATION = settings.invite_expire_seconds 

    async def update_admin_details(self, admin_id: str, input: AdminUpdateRequest, caller_role: str = None, caller_id: str = None):
        # Load the target user first. Previously this code assumed `user` was in scope and
        # caused a NameError when it wasn't. Fetch and validate early.
        user = await get_user_by_id(self.db, admin_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found.")
        
        # Role-based permission validation:
        # SUPER_ADMIN can edit anyone
        # ADMIN can edit ADMIN and HR
        # HR can edit HR only
        target_role = user.role
        
        if caller_role == "SUPER_ADMIN":
            # Super admin can edit anyone
            pass
        elif caller_role == "ADMIN":
            if target_role not in ["ADMIN", "HR"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="ADMIN can only edit ADMIN or HR roles"
                )
        elif caller_role == "HR":
            if target_role != "HR":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="HR can only edit HR roles"
                )
            # HR can edit themselves or other HRs
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to edit admin details"
            )

        # Check for requested role change (promotion/demotion)
        requested_role = getattr(input, "role", None)
        role_changed = requested_role is not None and requested_role != target_role
        # preserve the existing role as old_role for notifications
        old_role = target_role

        if role_changed:
            # Permission rules for role changes:
            # - SUPER_ADMIN: can change any user's role
            # - ADMIN: cannot touch SUPER_ADMINs, cannot assign SUPER_ADMIN, but may set ADMIN/HR
            # - HR: cannot change roles of anyone
            if caller_role == "SUPER_ADMIN":
                # allowed
                pass
            elif caller_role == "ADMIN":
                if target_role == "SUPER_ADMIN":
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN cannot modify SUPER_ADMIN accounts")
                if requested_role == "SUPER_ADMIN":
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN cannot assign SUPER_ADMIN role")
                # ADMIN can set ADMIN or HR
                if requested_role not in ["ADMIN", "HR"]:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN can only assign ADMIN or HR roles")
            elif caller_role == "HR":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR cannot change roles")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to change role")

            # Persist the role change immediately (role changes do not require email/name verification)
            try:
                updated_role_user = await update_user_details(self.db, user_id=admin_id, updates={"role": requested_role})
            except Exception as exc:
                logger.exception(f"Failed to persist role update for {admin_id}: %s", exc)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update role. Please try again later.")

            if not updated_role_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found.")

            # Refresh local user object and target_role
            user = updated_role_user
            target_role = user.role
            # Revoke existing refresh JTIs (force logout) for the user whose role changed
            try:
                user_id_str = str(user.user_id)
                # Revoke refresh JTIs
                active_refresh_key = f"active_refresh_jtis:{user_id_str}"
                try:
                    refresh_jtiset = await self.cache.smembers(active_refresh_key)
                except Exception:
                    refresh_jtiset = None

                if refresh_jtiset:
                    REFRESH_TOKEN_LIFESPAN = settings.access_refresh_token_expire_hours * 3600
                    revoked_refresh = 0
                    for jti in refresh_jtiset:
                        try:
                            jti_val = jti.decode() if isinstance(jti, bytes) else jti
                            await add_jti_to_blocklist(jti_val, self.cache, REFRESH_TOKEN_LIFESPAN)
                            revoked_refresh += 1
                        except Exception as inner_e:
                            logger.warning(f"Failed to add refresh JTI {jti} to blocklist for user {user_id_str}: {inner_e}")
                    try:
                        await self.cache.delete(active_refresh_key)
                    except Exception:
                        pass
                    logger.info(f"Revoked {revoked_refresh} refresh JTI(s) for user {user_id_str} after role change.")

                # Revoke active access JTIs as well so currently-used access tokens are invalidated immediately
                active_access_key = f"active_access_jtis:{user_id_str}"
                try:
                    access_jtiset = await self.cache.smembers(active_access_key)
                except Exception:
                    access_jtiset = None

                if access_jtiset:
                    ACCESS_TOKEN_LIFESPAN = settings.access_token_expire_minutes * 60
                    revoked_access = 0
                    for jti in access_jtiset:
                        try:
                            jti_val = jti.decode() if isinstance(jti, bytes) else jti
                            await add_jti_to_blocklist(jti_val, self.cache, ACCESS_TOKEN_LIFESPAN)
                            revoked_access += 1
                        except Exception as inner_e:
                            logger.warning(f"Failed to add access JTI {jti} to blocklist for user {user_id_str}: {inner_e}")
                    try:
                        await self.cache.delete(active_access_key)
                    except Exception:
                        pass
                    logger.info(f"Revoked {revoked_access} access JTI(s) for user {user_id_str} after role change.")

                # Set a short-lived cache flag to indicate frontend may want to show a forced-logout message
                try:
                    await self.cache.set(f"role_change_forced_logout:{user_id_str}", "1", ex=300)
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"Error during token revocation after role change for user {admin_id}: {e}")

            # Attempt to send a notification email to the affected administrator about the role change.
            try:
                # Use module-level alias send_admin_role_change_email (re-exported above)

                performed_by = None
                if caller_id:
                    try:
                        caller_user = await get_user_by_id(self.db, caller_id)
                        if caller_user:
                            performed_by = f"{caller_user.first_name} {caller_user.last_name or ''}".strip()
                    except Exception:
                        performed_by = None

                # Prefer the form-provided name (if any) when composing email notifications
                first_name_for_email = getattr(input, 'first_name', None) or (user.first_name if user else '')
                last_name_for_email = getattr(input, 'last_name', None)
                if last_name_for_email is None:
                    last_name_for_email = user.last_name if user else ''
                admin_display_name = f"{first_name_for_email} {last_name_for_email or ''}".strip() if user or first_name_for_email else None

                # Fire-and-forget the email; don't block the main flow on failures
                try:
                    await send_admin_role_change_email(
                        recipient_email=user.email,
                        admin_name=admin_display_name,
                        old_role=old_role,
                        new_role=requested_role,
                        performed_by=performed_by,
                        db=self.db,
                    )
                except Exception as mail_exc:
                    logger.warning(f"Role change email failed for user {admin_id}: {mail_exc}")
            except Exception:
                # Non-fatal - log and continue
                logger.exception("Unexpected error while sending role change email (non-fatal)")

        current_phone = getattr(user, "phone_number", "") or ""
        new_phone_value = str(input.phone_number).strip() if input.phone_number is not None else None
        phone_changed = (
            new_phone_value is not None and new_phone_value != str(current_phone).strip()
        )
        phone_update_payload = None

        updates = {}
        old_full_name = f"{user.first_name} {user.last_name or ''}".strip()
        name_changed = False
        if input.first_name is not None and input.first_name != user.first_name:
            updates["first_name"] = input.first_name
            name_changed = True
        if input.last_name is not None and input.last_name != user.last_name:
            updates["last_name"] = input.last_name
            name_changed = True
            
        is_email_change_requested = bool(input.new_email and input.new_email != user.email)
        
        if not name_changed and not is_email_change_requested:
            if phone_changed:
                phone_update_payload = await self._initiate_phone_update_flow(
                    user=user,
                    new_phone=new_phone_value or "",
                    current_phone=str(current_phone).strip(),
                )
                return ResponseBuilder.success(
                    "Phone number update pending confirmation. Verification email sent to the administrator.",
                    phone_update_payload,
                    status_code=status.HTTP_202_ACCEPTED
                )
            # If role change was requested and already persisted above, return success
            if role_changed:
                return ResponseBuilder.success(
                    "Role updated successfully.",
                    {"user_id": admin_id, "new_role": requested_role},
                    status_code=status.HTTP_200_OK
                )
            return ResponseBuilder.success("No fields were updated.", None, status_code=status.HTTP_200_OK)

        # --- Scenario A: Email Change (Bundles Name Change) ---
        if is_email_change_requested:
            if phone_changed and phone_update_payload is None:
                phone_update_payload = await self._initiate_phone_update_flow(
                    user=user,
                    new_phone=new_phone_value or "",
                    current_phone=str(current_phone).strip(),
                )

            new_email = str(input.new_email)
            approval_token = generate_token()

            admin_first_name = updates.get("first_name") or user.first_name
            admin_full_name = f"{updates.get('first_name', user.first_name)} {updates.get('last_name', user.last_name or '')}".strip()

            cache_data = {
                "user_id": str(user.user_id),
                "type": "email_update_approval",
                "old_email": user.email,
                "new_email": new_email,
                "name_updates": {
                    k: v for k, v in updates.items() if k in ["first_name", "last_name"]
                },
                "admin_first_name": admin_first_name,
                "admin_full_name": admin_full_name,
            }

            # Use custom expiration_days if provided, otherwise use default
            token_expire_seconds = self.LINK_EXPIRATION
            if input.expiration_days and input.expiration_days > 0:
                token_expire_seconds = input.expiration_days * 24 * 3600  # Convert days to seconds
            
            token_key = f"{self.VERIFY_KEY_PREFIX}{approval_token}"
            await self.cache.set(token_key, json.dumps(cache_data), ex=token_expire_seconds)

            encoded_new_email = quote_plus(new_email)
            approval_link = (
                f"{settings.get_api_url}/v1/admins/approve-email-update"
                f"?token={approval_token}"
                f"&user_id={str(user.user_id)}"
                f"&new_email={encoded_new_email}"
            )

            # Calculate expires_at for email display
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=token_expire_seconds)
            
            success_old_email = await send_email_change_transfer_notification(
                    old_email=user.email,
                    admin_name=old_full_name,
                    new_email=new_email,
                    approval_link=approval_link,
                    expires_at=expires_at,
                    db=self.db,
                )

            if not success_old_email:
                await self.cache.delete(token_key)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send approval email to the current admin address. Update aborted.")

            response_data = {
                "user_id": str(user.user_id),
                "verification_status": "PENDING_OLD_EMAIL_APPROVAL",
            }
            if phone_update_payload:
                response_data["phone_update_status"] = phone_update_payload

            message = "Approval email sent to the current admin address. Once approved, a verification will be sent to the new email."
            if phone_update_payload:
                message += " Phone number update confirmation email sent to the administrator."

            return ResponseBuilder.success(
                message,
                response_data,
                status_code=status.HTTP_202_ACCEPTED
            )

        # --- Scenario B: Name Change Only ---
        if name_changed and not is_email_change_requested:
            if phone_changed and phone_update_payload is None:
                phone_update_payload = await self._initiate_phone_update_flow(
                    user=user,
                    new_phone=new_phone_value or "",
                    current_phone=str(current_phone).strip(),
                )

            new_full_name = f"{updates.get('first_name') or user.first_name} {updates.get('last_name') or user.last_name or ''}".strip()
            verification_token = generate_token()
            
            cache_data = {
                "user_id": str(user.user_id),
                "type": "name_update",
                "updates": updates
            }
            # Use custom expiration_days if provided, otherwise use default
            token_expire_seconds = self.LINK_EXPIRATION
            if input.expiration_days and input.expiration_days > 0:
                token_expire_seconds = input.expiration_days * 24 * 3600  # Convert days to seconds
                
            token_key = f"{self.VERIFY_KEY_PREFIX}{verification_token}"
            await self.cache.set(token_key, json.dumps(cache_data), ex=token_expire_seconds)
            
            # Use backend API endpoint for verification links so the link performs the verification server-side
            verification_link = (
                f"{self.API_URL}/v1/admins/verify-name-update"
                f"?token={verification_token}"
                f"&user_id={str(user.user_id)}"
            )

            # Calculate expires_at for email display
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=token_expire_seconds)
            
            success_email = await send_name_update_verification_link(
                recipient_email=user.email,
                old_name=old_full_name,
                new_name=new_full_name,
                verification_link=verification_link,
                expires_at=expires_at,
                db=self.db,
            )
            
            if not success_email:
                await self.cache.delete(token_key)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send name update verification email. Update aborted.")
                
            response_data = {
                "user_id": admin_id,
                "verification_status": "PENDING_NAME_CONFIRM",
            }
            if phone_update_payload:
                response_data["phone_update_status"] = phone_update_payload

            message = "Name update verification link sent to your email. Name change pending confirmation."
            if phone_update_payload:
                message += " Phone number update confirmation email sent to the administrator."

            return ResponseBuilder.success(
                message,
                response_data,
                status_code=status.HTTP_202_ACCEPTED
            )
        
    async def _initiate_phone_update_flow(self, user, new_phone: str, current_phone: str) -> dict:
        """Create a phone update verification token and notify the administrator."""

        verification_token = generate_token()
        token_key = f"{self.VERIFY_KEY_PREFIX}{verification_token}"

        cache_payload = {
            "user_id": str(user.user_id),
            "type": "phone_update",
            "new_phone_number": new_phone,
            "old_phone_number": current_phone,
        }

        # Note: For phone updates initiated from name/email changes, we use the parent request's expiration
        # This method doesn't receive expiration_days directly, so it uses the default
        await self.cache.set(token_key, json.dumps(cache_payload), ex=self.LINK_EXPIRATION)

        admin_display_name = f"{user.first_name} {user.last_name or ''}".strip() or user.email

        # Use backend API endpoint so clicking the email button triggers server-side verification logic
        verification_link = (
            f"{self.API_URL}/v1/admins/confirm-phone-update"
            f"?token={verification_token}"
            f"&user_id={str(user.user_id)}"
        )

        email_sent = await send_phone_update_verification_link(
            recipient_email=user.email,
            admin_name=admin_display_name,
            old_phone=current_phone,
            new_phone=new_phone,
            verification_link=verification_link,
            db=self.db,
        )

        if not email_sent:
            await self.cache.delete(token_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send phone update confirmation email. Update aborted.",
            )

        return {
            "user_id": str(user.user_id),
            "requested_phone_number": new_phone,
            "verification_status": "PENDING_PHONE_CONFIRMATION",
            "expires_in_seconds": self.LINK_EXPIRATION,
        }

    async def verify_phone_update(self, token: str, user_id: str):
        """Finalize a pending phone number update request."""

        token_key = f"{self.VERIFY_KEY_PREFIX}{token}"
        cached_data_str = await self.cache.get(token_key)

        if not cached_data_str:
            return ResponseBuilder.success(
                "Verification link is invalid or already used.",
                None,
                status_code=status.HTTP_200_OK,
            )

        cached_data = json.loads(cached_data_str)

        if cached_data.get("type") != "phone_update" or str(cached_data.get("user_id")) != user_id:
            return ResponseBuilder.success(
                "Verification token is not valid for this operation.",
                None,
                status_code=status.HTTP_200_OK,
            )

        new_phone = cached_data.get("new_phone_number")
        if not new_phone:
            await self.cache.delete(token_key)
            return ResponseBuilder.success(
                "Phone update request no longer contains pending changes.",
                None,
                status_code=status.HTTP_200_OK,
            )

        try:
            updated_user = await update_user_details(
                self.db,
                user_id=user_id,
                updates={"phone_number": new_phone},
            )
        except Exception as exc:
            logger.error(f"Failed to persist phone update for admin {user_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update phone number. Please try again later.",
            )

        if not updated_user:
            await self.cache.delete(token_key)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found.")

        await self.cache.delete(token_key)

        return ResponseBuilder.success(
            "Phone number updated successfully.",
            {"user_id": user_id, "phone_number": new_phone},
            status_code=status.HTTP_200_OK,
        )

    async def verify_name_update(self, token: str, user_id: str):
        """Completes a pending name update."""
        token_key = f"{self.VERIFY_KEY_PREFIX}{token}"
        cached_data_str = await self.cache.get(token_key)

        if not cached_data_str:
            # Link was already used or expired. Treat as idempotent success to avoid 400 responses
            return ResponseBuilder.success(
                "Verification link is invalid or already used.",
                None,
                status_code=status.HTTP_200_OK
            )

        cached_data = json.loads(cached_data_str)

        if cached_data.get('type') != 'name_update' or str(cached_data.get('user_id')) != user_id:
            # Mismatched or tampered token — respond gracefully without a 400 to the client
            return ResponseBuilder.success(
                "Verification token is not valid for this operation.",
                None,
                status_code=status.HTTP_200_OK
            )

        updates = cached_data.get('updates', {})
        if not updates:
            await self.cache.delete(token_key)
            return ResponseBuilder.success("Name update already processed or no changes found.", None, status_code=status.HTTP_200_OK)

        updated_user = await update_user_details(
            self.db, 
            user_id=user_id, 
            updates=updates
        )

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database update failed.")

        await self.cache.delete(token_key)
        
        new_full_name = f"{updated_user.first_name} {updated_user.last_name or ''}".strip()
        
        await send_name_update_success_notification(updated_user.email, new_full_name, db=self.db)

        return ResponseBuilder.success(
            "Profile name updated successfully.",
            {"user_id": user_id, "first_name": updated_user.first_name, "last_name": updated_user.last_name},
            status_code=status.HTTP_200_OK
        )

    async def approve_email_update(self, token: str, user_id: str):
        """Handles approval from the existing admin email before contacting the new email."""
        token_key = f"{self.VERIFY_KEY_PREFIX}{token}"
        cached_data_str = await self.cache.get(token_key)

        if not cached_data_str:
            return ResponseBuilder.success(
                "Approval link is invalid or has already been used.",
                None,
                status_code=status.HTTP_200_OK
            )

        cached_data = json.loads(cached_data_str)

        if (
            cached_data.get("type") != "email_update_approval"
            or str(cached_data.get("user_id")) != user_id
        ):
            return ResponseBuilder.success(
                "Approval link is not valid for this administrator.",
                None,
                status_code=status.HTTP_200_OK
            )

        new_email = cached_data.get("new_email")
        old_email = cached_data.get("old_email")
        name_updates = cached_data.get("name_updates") or {}

        if not new_email or not old_email:
            await self.cache.delete(token_key)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incomplete approval data. Please initiate the email update again.")

        verification_token = generate_token()
        verification_key = f"{self.VERIFY_KEY_PREFIX}{verification_token}"

        stage_two_cache = {
            "user_id": user_id,
            "type": "email_update",
            "old_email": old_email,
            "new_email": new_email,
            "name_updates": name_updates,
            "admin_first_name": cached_data.get("admin_first_name"),
            "admin_full_name": cached_data.get("admin_full_name"),
        }

        await self.cache.set(verification_key, json.dumps(stage_two_cache), ex=self.LINK_EXPIRATION)

        encoded_new_email = quote_plus(new_email)
        encoded_success_url = quote_plus(f"{self.BASE_FRONTEND_URL}/auth/email-update-success")

        verification_link = (
            f"{settings.get_api_url}/v1/admins/complete-email-update-status"
            f"?token={verification_token}"
            f"&user_id={user_id}"
            f"&new_email={encoded_new_email}"
            f"&redirect_to={encoded_success_url}"
        )

        api_verification_info = {
            # Use get_api_url to include the API prefix and avoid double-/missing prefixes
            "endpoint": f"{settings.get_api_url}/v1/admins/verify-email-update",
            "method": "POST",
            "payload": {
                "token": verification_token,
                "user_id": user_id,
                "new_email": new_email,
            },
        }

        api_info_key = f"api_verify:{verification_token}"
        await self.cache.set(api_info_key, json.dumps(api_verification_info), ex=self.LINK_EXPIRATION)

        admin_first_name = stage_two_cache.get("admin_first_name") or stage_two_cache.get("admin_full_name") or old_email

        success_new_email = await send_email_update_verification_link(
            recipient_email=new_email,
            admin_name=admin_first_name,
            verification_link=verification_link,
            old_email=old_email,
            api_info=api_verification_info,
            db=self.db,
        )

        if not success_new_email:
            await self.cache.delete(verification_key)
            await self.cache.delete(api_info_key)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send verification email to the new address. Please retry the approval.")

        await self.cache.delete(token_key)

        return ResponseBuilder.success(
            "Approval confirmed. Verification email sent to the new address.",
            {
                "user_id": user_id,
                "new_email": new_email,
                "verification_status": "PENDING_NEW_EMAIL_CONFIRM",
            },
            status_code=status.HTTP_200_OK,
        )

    async def verify_email_update(self, input: UpdateEmailVerifyTokenRequest, is_api_request: bool = False):
        """
        Finalizes the email change, applies name updates, and blocks old tokens.
        """
        token_key = f"{self.VERIFY_KEY_PREFIX}{input.token}"
        cached_data_str = await self.cache.get(token_key)

        if not cached_data_str:
            error_msg = "Invalid or expired verification link."
            if is_api_request:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
            return ResponseBuilder.error(error_msg, [error_msg], status_code=status.HTTP_400_BAD_REQUEST)

        cached_data = json.loads(cached_data_str)
        
        if cached_data.get('type') != 'email_update' or str(cached_data.get('user_id')) != input.user_id or cached_data.get('new_email') != input.new_email:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token data integrity check failed.")
             
        # Set a temporary key to allow access during email update (300s expiry)
        temp_access_key = f"temp_access:{input.user_id}"
        await self.cache.set(temp_access_key, "1", ex=300)

        user = await get_user_by_id(self.db, input.user_id)
        if not user:
            await self.cache.delete(token_key) 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        
        # 1. Combine updates
        all_updates = cached_data.get("name_updates", {})
        all_updates["email"] = input.new_email
        
        # 2. Update DB with transaction safety
        try:
            updated_user = await update_user_details(
                self.db, 
                user_id=input.user_id, 
                updates=all_updates
            )
        except Exception as db_exc:
            logger.error(f"Database error during final email update for user {input.user_id}: {db_exc}")
            
            # Check for unique constraint violation
            if "duplicate key value violates unique constraint" in str(db_exc).lower():
                 raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The new email address is already registered to another account.")
            
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database update failed due to internal error.")


        if not updated_user:
            # If update_user_details returns None (meaning no row found or update failed silently)
            await self.cache.delete(token_key)
            if await get_user_by_id(self.db, input.user_id):
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database update failed. Record was present but update was not successful.")
            else:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found during update attempt.")

        user_id = input.user_id
        # Revoke all tracked JTIs for this user (if any)
        active_jtis_key = f"active_refresh_jtis:{user_id}"
        try:
            # Retrieve all JTIs in the set
            jtiset = await self.cache.smembers(active_jtis_key)
            if jtiset:
                REFRESH_TOKEN_LIFESPAN = settings.access_refresh_token_expire_hours * 3600
                for jti in jtiset:
                    try:
                        await add_jti_to_blocklist(jti.decode() if isinstance(jti, bytes) else jti, self.cache, REFRESH_TOKEN_LIFESPAN)
                    except Exception as inner_e:
                        logger.warning(f"Failed to add JTI {jti} to blocklist for user {user_id}: {inner_e}")
                # Remove the tracking set so all old sessions require fresh login
                await self.cache.delete(active_jtis_key)
                logger.info(f"Revoked {len(jtiset)} refresh JTI(s) for user {user_id} after email change.")
        except Exception as e:
            logger.error(f"Error during token revocation for user {user_id} after email change: {e}")
            # Log the failure but do not halt execution
            
        # ----------------------------------------------------------------------
        
        session_key = f"preserving_session:{input.user_id}"
        preserving_session = await self.cache.get(session_key)
        
        await self.cache.delete(token_key)

        # Set successful update flag (for frontend redirect utility)
        email_update_key = f"email_update_success:{input.user_id}"
        await self.cache.set(email_update_key, "1", ex=300)

        # Clean up session preservation flag
        if preserving_session:
            await self.cache.delete(session_key)
            
        # The session is revoked; enforce a fresh login by redirecting with a status flag.
        return ResponseBuilder.success(
            "Admin email updated successfully. Session revoked. User must re-authenticate.",
            {
                "user_id": input.user_id, 
                "new_email": input.new_email,
                "preserve_session": False, # Enforce fresh login
                "redirect_url": f"{self.BASE_FRONTEND_URL}/auth?status=email_updated&new_email={quote_plus(input.new_email)}"
            }, 
            status_code=status.HTTP_200_OK
        )

    async def update_admin_email(self, user_id: str, new_email: str, db: AsyncSession):
        try:
            # Generate verification token
            verification_token = str(uuid4())
            
            # Store in Redis with expiry
            await self.cache.set(
                f"email_update:{verification_token}",
                json.dumps({
                    "user_id": user_id,
                    "new_email": new_email
                }),
                ex=3600 
            )
            
            encoded_email = quote_plus(new_email)
            verification_link = (
                f"{settings.frontend_url}/auth/verify-email-update"  # Changed this line
                f"?token={verification_token}"
                f"&user_id={user_id}"
                f"&new_email={encoded_email}"
            )
            
            # Send verification email (pass DB session so saved template is used)
            await send_email_update_verification_link(
                recipient_email=new_email,
                admin_name="",
                verification_link=verification_link,
                old_email="",
                db=db,
            )
            
            return ResponseBuilder.success(
                message="Verification email sent. Please check your inbox.",
                data={"verification_sent": True}
            )
            
        except Exception as e:
            logger.exception("Error in update_admin_email: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate email update process"
            )