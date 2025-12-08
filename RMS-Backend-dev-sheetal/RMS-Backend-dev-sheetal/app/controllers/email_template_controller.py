from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.standard_response_utils import ResponseBuilder
from app.services.config_service.email_template_service import EmailTemplateService
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplateUpdateRequest


async def handle_get_email_template_controller(template_key: str, db: AsyncSession):
    try:
        template_data = await EmailTemplateService.get_template(db, template_key)
        return JSONResponse(content=ResponseBuilder.success(message=f"Template '{template_key}' retrieved.", data=template_data), status_code=200)
    except Exception as e:
        return JSONResponse(content=ResponseBuilder.server_error(message=f"Failed to retrieve template: {e}"), status_code=500)


async def handle_preview_email_template_controller(request: EmailTemplatePreviewRequest):
    try:
        rendered_subject, rendered_body = await EmailTemplateService.get_template_preview_content(
            template_subject=request.template_subject,
            template_body=request.template_body,
            sample_context=request.sample_context,
        )
        return JSONResponse(content=ResponseBuilder.success(message="Rendered preview", data={"rendered_subject": rendered_subject, "rendered_html_body": rendered_body}), status_code=200)
    except ValueError as e:
        return JSONResponse(content=ResponseBuilder.error(message=str(e)), status_code=400)
    except Exception as e:
        return JSONResponse(content=ResponseBuilder.server_error(message=f"Preview rendering failed: {e}"), status_code=500)


async def handle_update_email_template_controller(request: EmailTemplateUpdateRequest, db: AsyncSession):
    try:
        success = await EmailTemplateService.save_email_template(db, request.template_key, request.subject_template, request.body_template_html)
        if success:
            return JSONResponse(content=ResponseBuilder.created(message=f"Template '{request.template_key}' saved."), status_code=201)
        return JSONResponse(content=ResponseBuilder.error(message="Failed to save template"), status_code=500)
    except Exception as e:
        return JSONResponse(content=ResponseBuilder.server_error(message=f"Failed to save template: {e}"), status_code=500)
