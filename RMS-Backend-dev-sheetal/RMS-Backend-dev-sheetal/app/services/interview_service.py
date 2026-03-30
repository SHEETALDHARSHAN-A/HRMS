import logging
import asyncio
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy import cast, String

from app.db.models.scheduling_model import Scheduling
from app.db.models.resume_model import Profile
from app.db.redis_manager import RedisManager
from app.utils.email_utils import send_otp_email
# The OTP generator used by the auth services is `generate_otp_code` in
# `app.utils.authentication_utils`. Import it here and alias to `generate_otp`
# so the rest of this module can call `generate_otp()` as expected.
from app.utils.authentication_utils import generate_otp_code as generate_otp
from app.config.app_config import AppConfig

# Import LiveKit SDK
from livekit.api import LiveKitAPI, AccessToken
from livekit.api.access_token import VideoGrants
from livekit.protocol.room import CreateRoomRequest

settings = AppConfig()
logger = logging.getLogger(__name__)

# --- LiveKit Configuration ---
# Ensure these are in your .env file
LIVEKIT_URL = settings.livekit_url # e.g., 'http://localhost:7880'
LIVEKIT_API_KEY = settings.livekit_api_key
LIVEKIT_API_SECRET = settings.livekit_api_secret

class InterviewAuthService:

    @staticmethod
    async def validate_token_and_send_otp(
        email: str, 
        token: str, 
        db: AsyncSession
    ) -> dict:
        """
        1. Validate email and interview_token against the scheduling_interviews table.
        2. Check if the interview status is 'scheduled'.
        3. Send an OTP if valid.
        """
        # We'll compare the token as text to be resilient to DB column type mismatches
        # (some deployments may have the interview_token column stored as text).
        token_str = token

        # Query for the schedule entry, joining with Profile to check email
        query = (
            select(Scheduling)
            .join(Profile, Scheduling.profile_id == Profile.id)
            .where(
                cast(Scheduling.interview_token, String) == token_str,
                Profile.email == email,
            )
        )
        result = await db.execute(query)
        scalars = result.scalars()
        if asyncio.iscoroutine(scalars) or hasattr(scalars, '__await__'):
            scalars = await scalars
        schedule = scalars.first() if scalars is not None else None
        if asyncio.iscoroutine(schedule) or hasattr(schedule, '__await__'):
            schedule = await schedule

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview token or email is incorrect.",
            )

        schedule_status = str(getattr(schedule, "status", "") or "").lower()
        if schedule_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This interview has already been completed.",
            )

        if schedule_status != "scheduled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interview status is '{schedule.status}'. Cannot proceed.",
            )

        interview_type = str(getattr(schedule, "interview_type", "Agent_interview") or "Agent_interview").lower()
        if any(tag in interview_type for tag in ("coding", "apti", "aptitude", "mcq", "assessment")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This round is an assessment round. Please use the coding/aptitude assessment flow.",
            )

        if any(tag in interview_type for tag in ("in_person", "in-person", "offline")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This is an in-person interview round. Please check the meeting room details with your coordinator.",
            )

        scheduled_at = getattr(schedule, "scheduled_datetime", None)
        if scheduled_at is not None:
            if getattr(scheduled_at, "tzinfo", None) is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

            join_window_open = scheduled_at - timedelta(minutes=5)
            now_utc = datetime.now(timezone.utc)
            if now_utc < join_window_open:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interview room access opens 5 minutes before the scheduled start time.",
                )

        # Generate and send OTP
        try:
            redis_client = RedisManager.get_client()
            otp_code = generate_otp()
            # Use a specific prefix for interview OTPs
            redis_key = f"interview_otp:{email}"
            await redis_client.set(redis_key, otp_code, ex=settings.otp_expire_seconds)
            
            # Send OTP email
            await send_otp_email(to_email=email, otp_code=otp_code, subject="Your Interview Verification Code", db=db)
            
            return {"message": "OTP has been sent to your email."}
            
        except Exception as e:
            logger.error(f"Error during OTP generation/sending for interview: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP.",
            )

    @staticmethod
    async def verify_otp_and_get_room(
        email: str, 
        token: str, 
        otp: str, 
        db: AsyncSession
    ) -> dict:
        """
        1. Verify OTP from Redis.
        2. If valid, create a LiveKit room and generate a token for the candidate.
        """
        
        try:
            redis_client = RedisManager.get_client()
            redis_key = f"interview_otp:{email}"
            stored_otp = await redis_client.get(redis_key)
            
            if not stored_otp or stored_otp != otp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OTP.",
                )
            
            # OTP is valid, clear it
            await redis_client.delete(redis_key)

        except Exception as e:
            logger.error(f"Redis error during OTP verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error verifying OTP.",
            )

        # Fetch schedule again to get profile name
        # Use text comparison to be tolerant of DB schema differences
        token_str = token

        query = (
            select(Scheduling)
            .where(cast(Scheduling.interview_token, String) == token_str)
        )
        result = await db.execute(query)
        scalars = result.scalars()
        if asyncio.iscoroutine(scalars) or hasattr(scalars, '__await__'):
            scalars = await scalars
        schedule = scalars.first() if scalars is not None else None
        if asyncio.iscoroutine(schedule) or hasattr(schedule, '__await__'):
            schedule = await schedule

        # Scheduling model in this codebase does not define a `profile` relationship
        # on the Scheduling class. Load the Profile explicitly if needed.
        profile = None
        if schedule:
            # Try to use attribute if relationship exists
            profile = getattr(schedule, 'profile', None)
            if profile is None:
                try:
                    profile = await db.get(Profile, schedule.profile_id)
                except Exception:
                    profile = None

        if not schedule or not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview schedule not found after OTP verification.",
            )

        # --- LiveKit Room and Token Generation ---
        if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
            logger.error("LiveKit settings are not configured in the environment.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Interview service is not configured.",
            )
            
        try:
            # The interview_token (as a string) will be the unique room name
            room_name = token
            # Use the explicitly loaded profile (avoid accessing schedule.profile which may not exist)
            participant_name = (profile.name if profile and getattr(profile, 'name', None) else "Candidate")
            participant_identity = f"candidate-{schedule.profile_id}"

            # 1. Create the room on the LiveKit server using LiveKitAPI
            lkapi = LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            create_req = CreateRoomRequest(name=room_name, empty_timeout=600, max_participants=2)
            try:
                await lkapi.room.create_room(create_req)
                logger.info(f"LiveKit room created: {room_name}")
            except Exception as e:
                # It's okay if the room already exists (e.g., agent joined first)
                logger.warning(f"Could not create room (it may already exist): {e}")

            # 2. Generate an access token for the candidate
            # 2. Generate an access token for the candidate using AccessToken and VideoGrants
            access_token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            grants = VideoGrants(room=room_name, room_join=True, can_publish=True, can_subscribe=True)
            access_token.with_grants(grants)
            access_token.with_identity(participant_identity)
            access_token.with_name(participant_name)

            jwt_token = access_token.to_jwt()

            return {
                "livekit_url": LIVEKIT_URL,
                "livekit_token": jwt_token,
                "room_name": room_name,
                "participant_name": participant_name
            }

        except Exception as e:
            logger.error(f"LiveKit token generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize interview session.",
            )