# File: app/api/v1/config_routes.py (FIXED)

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplateUpdateRequest
from app.services.config_service.email_template_service import EmailTemplateService
from app.utils.email_utils import (
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
from app.db.connection_manager import get_db
from app.utils.standard_response_utils import ResponseBuilder 

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])



# --- FIX: Removed response_model=EmailTemplateResponse ---
@router.get("/email/template/{template_key}") 
async def get_email_template(
    template_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to retrieve the current saved (or default) email template placeholders.
    Used by the frontend to populate the subject/body fields in the scheduling screen.
    """
    try:
        template_data = await EmailTemplateService.get_template(db, template_key)

        # Controller-level fallback: if service returned placeholder "No Default...",
        # replace with our known defaults (helps when a running service hasn't been
        # restarted after changes).
        subject = template_data.get('subject_template') if isinstance(template_data, dict) else None
        body = template_data.get('body_template_html') if isinstance(template_data, dict) else None

        def needs_default(s: str | None) -> bool:
            return not s or s.strip().startswith('No Default')

        if needs_default(subject) or needs_default(body):
            # Normalize key and map to getter
            key_map = {
                'CANDIDATE_INTERVIEW_SCHEDULED': get_default_interview_template_content,
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
            if getter:
                default_subject, default_body = getter()
                # Only replace missing/default values
                if needs_default(subject):
                    template_data['subject_template'] = default_subject
                if needs_default(body):
                    template_data['body_template_html'] = default_body
                logger.info(f"Controller fallback: returned defaults for template '{template_key}' using {getter.__name__}")
            else:
                logger.debug(f"Controller fallback: no default mapping for '{template_key}'")

        return ResponseBuilder.success(
            status_code=status.HTTP_200_OK,
            message=f"Template '{template_key}' retrieved successfully.",
            data=template_data
        )

    except Exception as e:
        logger.error(f"Error retrieving email template {template_key}: {e}")
        return ResponseBuilder.server_error(
            message="Error retrieving template from backend."
        )
    

# --- FIX: Removed response_model=EmailTemplatePreviewResponse ---
@router.post("/email/preview")
async def preview_email_template(request: EmailTemplatePreviewRequest):
    """
    Endpoint to preview an email template by rendering it with sample data.
    """
    try:
        # Calls service for preview (uses utility, no DB)
        rendered_subject, rendered_body = await EmailTemplateService.get_template_preview_content(
            template_subject=request.template_subject,
            template_body=request.template_body,
            sample_context=request.sample_context
        )
        
        response_data = {
            "rendered_subject": rendered_subject,
            "rendered_html_body": rendered_body
        }
        
        return ResponseBuilder.success(
            status_code=status.HTTP_200_OK, 
            message="Email template rendered successfully for preview.", 
            data=response_data
        )

    except ValueError as e:
        return ResponseBuilder.error(
            status_code=status.HTTP_400_BAD_REQUEST, 
            message=str(e)
        )
    except Exception as e:
        logger.error(f"Error rendering email preview in controller: {e}")
        return ResponseBuilder.server_error(
            message="Internal server error during template rendering."
        )

# This endpoint is already correct as it has no response_model
@router.post("/email/template")
async def update_email_template(
    request: EmailTemplateUpdateRequest, 
    db: AsyncSession = Depends(get_db) # Inject DB dependency
):
    """
    Endpoint to save or update a custom email template (subject and body) in the database.
    This uses an upsert logic based on the template_key.
    """
    try:
        # Calls service to save the template (uses repository, requires DB)
        success = await EmailTemplateService.save_email_template(
            db=db,
            template_key=request.template_key,
            subject_template=request.subject_template,
            body_template_html=request.body_template_html
        )
        
        if success:
            return ResponseBuilder.created(
                message=f"Email template '{request.template_key}' updated successfully."
            )
        else:
            return ResponseBuilder.error(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 message="Template save failed due to unknown database issue."
            )

    except RuntimeError as e:
        logger.error(f"Database error saving template {request.template_key}: {e}")
        return ResponseBuilder.server_error(
            message="Database error during template save. Please check logs."
        )
    except Exception as e:
        logger.error(f"Unhandled error saving template {request.template_key}: {e}")
        return ResponseBuilder.server_error(
            message="An unexpected error occurred."
        )


@router.post("/email/template/{template_key}/reset")
async def reset_email_template(
    template_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Resets a saved email template to the server-side default. Returns 200 on success, 404 if no default exists.
    """
    try:
        success = await EmailTemplateService.reset_template_to_default(db=db, template_key=template_key)
        if success:
            return ResponseBuilder.success(
                status_code=status.HTTP_200_OK,
                message=f"Template '{template_key}' reset to default."
            )
        else:
            return ResponseBuilder.error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"No server-side default configured for template '{template_key}'."
            )
    except Exception as e:
        logger.error(f"Error resetting template {template_key}: {e}")
        return ResponseBuilder.server_error(
            message="Error resetting template to default."
        )