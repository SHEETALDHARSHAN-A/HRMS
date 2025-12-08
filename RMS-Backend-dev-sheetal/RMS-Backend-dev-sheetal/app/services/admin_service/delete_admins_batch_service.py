# app/services/admin_service/delete_admins_batch_service.py

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.email_utils import send_admin_removal_email 
from app.utils.standard_response_utils import ResponseBuilder
from app.schemas.authentication_request import DeleteAdminsBatchRequest
from app.db.repository.user_repository import delete_users_by_id_and_type

class DeleteAdminsBatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_admins(self, input: DeleteAdminsBatchRequest, caller_role: str = None, caller_id: str = None):
        user_ids_to_delete = input.user_ids
        
        if not user_ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user IDs provided for deletion."
            )

        # 1. Perform batch deletion with role validation
        # Only allow deletion of admin roles (SUPER_ADMIN, ADMIN, HR), not CANDIDATE
        deleted_count, deleted_users = await delete_users_by_id_and_type(
            self.db, 
            user_ids_to_delete, 
            allowed_roles=["SUPER_ADMIN", "ADMIN", "HR"],  # Only delete admin roles
            caller_role=caller_role, 
            caller_id=caller_id
        )
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching Admin accounts found or deleted. Ensure IDs are correct and users are not SUPER_ADMIN."
            )

        # 2. Send notification email for EACH deleted admin asynchronously
        for user in deleted_users:
            admin_name = f"{user.first_name} {user.last_name}".strip()
            # We don't await this email call to prevent one failed email from blocking the others.
            # The email utility handles thread execution.
            await send_admin_removal_email(
                recipient_email=user.email,
                admin_name=admin_name,
                db=self.db
            )

        message = f"Successfully deleted {deleted_count} admin accounts."

        return ResponseBuilder.success(
            message,
            {"deleted_ids": [str(user.user_id) for user in deleted_users], "deleted_count": deleted_count},
            status_code=status.HTTP_200_OK
        )