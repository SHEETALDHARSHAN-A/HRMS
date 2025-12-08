# app/services/authentication_service/check_email_service.py

from typing import Any, Dict
import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository.user_repository import get_user_by_email

from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_helpers import validate_input_email

class CheckUserExistenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)

    async def check_email_status(self, email: str) -> Dict[str, Any]:
        """
        Checks if an email exists in the PostgreSQL database.
        Returns a dictionary response indicating availability status for direct use in controller.
        """
        try:
            # Reuses existing helper for basic email format validation
            validate_input_email(email)
        except HTTPException:
            # Return a controlled bad request response for invalid format
            return {
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid email format.",
                "data": {"is_available": False, "user_status": "INVALID_FORMAT"}
            }

        # Normalize email for consistent lookup (trim and lowercase)
        normalized_email = email.strip().lower()
        user = await get_user_by_email(self.db, normalized_email)

        # Debug log to help trace why 403/200 responses are happening
        try:
            self.logger.info(f"check_email_status: original=%s, normalized=%s, found=%s", email, normalized_email, bool(user))
            if user:
                self.logger.info(f"Found user: id=%s, email=%s, role=%s", getattr(user, 'user_id', 'N/A'), getattr(user, 'email', 'N/A'), getattr(user, 'role', 'N/A'))
        except Exception:
            # best-effort logging; don't raise
            pass

        if user:
            # User is present -> return 200 OK so frontend can proceed to sign-in
            return {
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "User with this email exists. You may sign in.",
                "data": {"is_available": False, "user_status": "EXIST"}
            }

        # User is not present -> return 403 Forbidden so frontend knows sign-in should be disabled
        return {
            "success": False,
            "status_code": status.HTTP_403_FORBIDDEN,
            "message": "User with this email does not exist.",
            "data": {"is_available": True, "user_status": "NOT_EXIST"}
        }