import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.config.app_config import AppConfig
from app.db.connection_manager import get_db
from app.schemas.interview_completion_request import InterviewCompletionRequest
from app.schemas.standard_response import StandardResponse
from app.services.interview_completion_service import InterviewCompletionService
from app.services.interview_service import InterviewAuthService
from app.utils.standard_response_utils import ResponseBuilder


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interview", tags=["Interview"])

class ValidateTokenRequest(BaseModel):
    email: EmailStr
    token: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    token: str
    otp: str


def _verify_internal_token(x_internal_token: str | None = Header(None)) -> bool:
    config = AppConfig()
    if not config.internal_service_token:
        raise HTTPException(status_code=403, detail="Internal interview completion endpoint is disabled")
    if x_internal_token != config.internal_service_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True

@router.post("/validate-token")
async def validate_interview_token(
    request: ValidateTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for a candidate to validate their interview token and email.
    If valid, sends an OTP to their email.
    """
    return await InterviewAuthService.validate_token_and_send_otp(
        email=request.email,
        token=request.token,
        db=db
    )

@router.post("/verify-otp")
async def verify_interview_otp(
    request: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for a candidate to verify their OTP.
    If valid, returns a LiveKit URL and token to join the interview room.
    """
    return await InterviewAuthService.verify_otp_and_get_room(
        email=request.email,
        token=request.token,
        otp=request.otp,
        db=db
    )


@router.post(
    "/complete",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete interview and trigger evaluation lifecycle",
)
async def complete_interview_route(
    request: InterviewCompletionRequest,
    _: bool = Depends(_verify_internal_token),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = InterviewCompletionService(db)
        payload = await service.complete_and_evaluate(
            token=request.token,
            email=str(request.email),
            session_id=request.session_id,
            final_notes=request.final_notes,
        )
        return ResponseBuilder.success(
            message="Interview completed and candidate evaluated.",
            data=payload,
        )
    except HTTPException as exc:
        return ResponseBuilder.error(message=exc.detail, status_code=exc.status_code)
    except Exception as exc:
        logger.error("Error completing interview lifecycle: %s", exc, exc_info=True)
        return ResponseBuilder.server_error("Unable to complete interview lifecycle.")