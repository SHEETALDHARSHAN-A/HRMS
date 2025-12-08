# app/services/admin_service/get_admin_by_id_service.py

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository.user_repository import get_user_by_id
from app.utils.standard_response_utils import ResponseBuilder

class GetAdminByIdService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_admin_details(self, admin_id: str):
        user = await get_user_by_id(self.db, admin_id)

        if not user or user.role not in ["SUPER_ADMIN", "ADMIN", "HR"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin with ID '{admin_id}' not found."
            )
        
        return ResponseBuilder.success(
            "Admin details retrieved successfully.",
            {
                "user_id": str(user.user_id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": user.role,  # Return role instead of user_type
                "phone_number": getattr(user, "phone_number", None),
            },
            status_code=status.HTTP_200_OK
        )