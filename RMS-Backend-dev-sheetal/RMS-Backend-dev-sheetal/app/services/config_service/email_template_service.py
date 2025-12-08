# app/services/config_service/email_template_service.py

import logging
import asyncio
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
# Import the new repository and utility
from app.db.repository.config_repository import ConfigRepository 
from app.utils.email_utils import (
    get_preview_email_content,
    get_default_interview_template_content,
    get_default_admin_invite_template_content,
    get_default_admin_role_update_template_content,
    get_default_admin_delete_template_content,
    get_default_otp_template_content,
    get_default_email_update_verification_template_content,
    get_default_email_change_transfer_notification_template_content,
    get_default_name_update_verification_template_content,
    get_default_name_update_success_template_content,
    get_default_phone_update_verification_template_content,
    get_default_otp_for_email_update_template_content,
)

logger = logging.getLogger(__name__)

class EmailTemplateService:
    
    # --- PREVIEW FUNCTIONALITY ---
    @staticmethod
    async def get_template(db: AsyncSession, template_key: str) -> Dict[str, str]:
        """
        Retrieves a stored template by key. If no custom template is found, 
        it returns the hardcoded default content placeholders.
        """
        template_record = await ConfigRepository.get_template_by_key(db, template_key)
        
        if template_record:
            return {
                "template_key": template_record.template_key,
                "subject_template": template_record.subject_template,
                "body_template_html": template_record.body_template_html,
            }
        else:
            # Normalize key to uppercase for flexible matching (frontend/backend may differ)
            template_key_upper = template_key.upper()

            # Use structured methods to retrieve hardcoded defaults matching frontend keys
            key_map = {
                'CANDIDATE_INTERVIEW_SCHEDULED': get_default_interview_template_content,
                # Frontend historically used 'interview_invite' as a template key.
                # Normalize common variants to the same default getter to ensure
                # saved templates (regardless of casing) are found or fallback
                # to the same default content.
                'INTERVIEW_INVITE': get_default_interview_template_content,
                'INTERVIEW_INVITATION': get_default_interview_template_content,
                'ADMIN_INVITE': get_default_admin_invite_template_content,
                'ADMIN_INVITATION': get_default_admin_invite_template_content,
                'ADMIN_ROLE_UPDATE': get_default_admin_role_update_template_content,
                'ADMIN_ROLE_CHANGE': get_default_admin_role_update_template_content,
                'ADMIN_DELETE': get_default_admin_delete_template_content,
                'ADMIN_ACCOUNT_DELETION': get_default_admin_delete_template_content,
                # OTP and verification flows
                'OTP': get_default_otp_template_content,
                'OTP_VERIFICATION': get_default_otp_template_content,
                'OTP_EMAIL': get_default_otp_template_content,
                'EMAIL_UPDATE_VERIFICATION': get_default_email_update_verification_template_content,
                'EMAIL_CHANGE_TRANSFER_NOTIFICATION': get_default_email_change_transfer_notification_template_content,
                'EMAIL_TRANSFER_NOTIFICATION': get_default_email_change_transfer_notification_template_content,
                'NAME_UPDATE_VERIFICATION': get_default_name_update_verification_template_content,
                'NAME_UPDATE_SUCCESS': get_default_name_update_success_template_content,
                'PHONE_UPDATE_VERIFICATION': get_default_phone_update_verification_template_content,
                'OTP_FOR_EMAIL_UPDATE': get_default_otp_for_email_update_template_content,
            }

            getter = key_map.get(template_key_upper)
            if getter:
                default_subject, default_body = getter()
                logger.info(f"No DB template for key '{template_key}', using default from getter '{getter.__name__}'")
            else:
                logger.warning(f"No DB template and no default mapping for key '{template_key}' (normalized '{template_key_upper}')")
                default_subject = "No Default Subject Available"
                default_body = "No Default Body Available"

            return {
                "template_key": template_key,
                "subject_template": default_subject,
                "body_template_html": default_body,
            }

    @staticmethod
    async def get_template_preview_content(template_subject: str, template_body: str, sample_context: Dict[str, Any]) -> Tuple[str, str]:
        """
        Async wrapper to render subject/body for preview using utility function.
        Returns (rendered_subject, rendered_body).
        """
        try:
            # Use to_thread in case rendering becomes CPU-bound in future
            rendered_subject, rendered_body = await asyncio.to_thread(
                get_preview_email_content,
                template_subject,
                template_body,
                sample_context,
            )
            return rendered_subject, rendered_body
        except Exception as e:
            logger.error(f"Error rendering template preview in service: {e}")
            # Re-raise to let controller handle the response formatting
            raise

    # --- UPDATE/SAVE FUNCTIONALITY ---
    @staticmethod
    async def save_email_template(
        db: AsyncSession, 
        template_key: str, 
        subject_template: str, 
        body_template_html: str
    ) -> bool:
        """
        Saves or updates the custom email template in the database using the repository.
        """
        try:
            # Calls the repository function to persist the data (DB interaction needed)
            await ConfigRepository.save_or_update_email_template(
                db, template_key, subject_template, body_template_html
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save email template in service: {e}")
            raise RuntimeError("Database error during template save.") from e

    @staticmethod
    async def reset_template_to_default(db: AsyncSession, template_key: str) -> bool:
        """
        Resets the stored template for `template_key` to the server-side default.
        Returns True if the repository upsert succeeded, False if no default exists.
        """
        try:
            # Map template_key to default getter functions defined in email_utils
            key_map = {
                'CANDIDATE_INTERVIEW_SCHEDULED': get_default_interview_template_content,
                'INTERVIEW_INVITE': get_default_interview_template_content,
                'INTERVIEW_INVITATION': get_default_interview_template_content,
                'ADMIN_INVITE': get_default_admin_invite_template_content,
                'ADMIN_INVITATION': get_default_admin_invite_template_content,
                'ADMIN_ROLE_UPDATE': get_default_admin_role_update_template_content,
                'ADMIN_ROLE_CHANGE': get_default_admin_role_update_template_content,
                'ADMIN_DELETE': get_default_admin_delete_template_content,
                'ADMIN_ACCOUNT_DELETION': get_default_admin_delete_template_content,
                'OTP': get_default_otp_template_content,
                'OTP_VERIFICATION': get_default_otp_template_content,
                'EMAIL_UPDATE_VERIFICATION': get_default_email_update_verification_template_content,
                'EMAIL_CHANGE_TRANSFER_NOTIFICATION': get_default_email_change_transfer_notification_template_content,
                'NAME_UPDATE_VERIFICATION': get_default_name_update_verification_template_content,
                'NAME_UPDATE_SUCCESS': get_default_name_update_success_template_content,
                'PHONE_UPDATE_VERIFICATION': get_default_phone_update_verification_template_content,
                'OTP_FOR_EMAIL_UPDATE': get_default_otp_for_email_update_template_content,
            }

            getter = key_map.get(template_key.upper())
            if not getter:
                logger.debug(f"No server-side default configured for template key: {template_key}")
                return False

            subject, body = getter()

            # Persist the default using the repository upsert
            await ConfigRepository.save_or_update_email_template(db, template_key, subject, body)
            logger.info(f"Reset template '{template_key}' to server-side default.")
            return True
        except Exception as e:
            logger.error(f"Failed to reset template '{template_key}' to default: {e}")
            raise