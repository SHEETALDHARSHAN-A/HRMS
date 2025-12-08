# app/services/admin_service/get_all_admin_service.py

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.standard_response_utils import ResponseBuilder
from app.db.repository.user_repository import get_all_admins_details

class GetAllAdminsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_admins(self, caller_role: str = None):
        """
        Get all admins based on caller's role:
        - SUPER_ADMIN: sees all admins (SUPER_ADMIN, ADMIN, HR)
        - ADMIN: sees ADMIN and HR
        - HR: sees HR only
        """
        admin_list = await get_all_admins_details(self.db, caller_role=caller_role)

        return ResponseBuilder.success(
            "Admin list retrieved successfully.",
            {"admins": admin_list},
            status_code=status.HTTP_200_OK
        )