import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.db.connection_manager import get_db
from app.schemas.candidate_status_notification_request import CandidateStatusNotificationRequest
from app.services.candidate_status_notification_service import CandidateStatusNotificationService
from app.utils.standard_response_utils import ResponseBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate-status", tags=["Candidate Status"])


def _verify_internal_token(x_internal_token: str | None = Header(None)) -> bool:
    config = AppConfig()
    if not config.internal_service_token:
        raise HTTPException(status_code=403, detail="Internal candidate status endpoint is disabled")
    if x_internal_token != config.internal_service_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


@router.post("/notify")
async def notify_candidate_status(
    request: CandidateStatusNotificationRequest,
    _: bool = Depends(_verify_internal_token),
    db: AsyncSession = Depends(get_db),
):
    service = CandidateStatusNotificationService(db)
    result = await service.send_status_email(
        profile_id=request.profile_id,
        round_id=request.round_id,
        result=request.result,
        reason=request.reason,
        source=request.source,
    )

    if not result.get("sent"):
        return ResponseBuilder.error(
            message="Candidate status email was not sent.",
            errors=[result.get("reason") or "send_failed"],
            data=result,
        )

    return ResponseBuilder.success(
        message="Candidate status email sent.",
        data=result,
    )
