from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.email_template_controller import (
    handle_get_email_template_controller,
    handle_preview_email_template_controller,
    handle_update_email_template_controller,
)
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplateUpdateRequest
from app.db.connection_manager import get_db

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])


@router.get("/{template_key}")
async def get_email_template(template_key: str, db: AsyncSession = Depends(get_db)):
    return await handle_get_email_template_controller(template_key, db)


@router.post("/preview")
async def preview_email_template(request: EmailTemplatePreviewRequest):
    return await handle_preview_email_template_controller(request)


@router.post("")
async def update_email_template(request: EmailTemplateUpdateRequest, db: AsyncSession = Depends(get_db)):
    return await handle_update_email_template_controller(request, db)
