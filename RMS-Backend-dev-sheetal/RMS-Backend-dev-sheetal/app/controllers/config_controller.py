# File: app/api/v1/config_routes.py (FINAL)

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
# Import the new schema and service
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplatePreviewResponse, EmailTemplateUpdateRequest
from app.services.config_service.email_template_service import EmailTemplateService
# Import DB dependency and standard response utility
from app.db.connection_manager import get_session # Assuming this is your dependency
from app.utils.standard_response_utils import ResponseBuilder 

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])

@router.post("/email/preview", response_model=EmailTemplatePreviewResponse)
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

@router.post("/email/template")
async def update_email_template(
    request: EmailTemplateUpdateRequest, 
    db: AsyncSession = Depends(get_session) # Inject DB dependency
):
    """
    [NEW] Endpoint to save or update a custom email template (subject and body) in the database.
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
            # Should be caught by service error, but as a fallback
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