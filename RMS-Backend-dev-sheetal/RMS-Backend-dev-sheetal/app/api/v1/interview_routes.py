from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.db.connection_manager import get_db
from app.services.interview_service import InterviewAuthService

router = APIRouter(prefix="/interview", tags=["Interview"])

class ValidateTokenRequest(BaseModel):
    email: EmailStr
    token: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    token: str
    otp: str

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