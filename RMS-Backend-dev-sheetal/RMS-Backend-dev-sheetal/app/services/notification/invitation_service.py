from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.standard_response_utils import ResponseBuilder
from app.db.repository.notification_repository import (
    fetch_invitations_by_inviter,
    get_invitation_stats_db,
    fetch_user_by_id,
)


class InvitationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_invitations_by_inviter(self, user_id: str, status_filter: Optional[str] = None) -> dict:
        try:
            invitations = await fetch_invitations_by_inviter(self.db, user_id, status_filter)
            invitation_list = []
            for invitation in invitations:
                invitation_data = {
                    "invitation_id": str(invitation.invitation_id),
                    "invited_email": invitation.invited_email,
                    "invited_first_name": invitation.invited_first_name,
                    "invited_last_name": invitation.invited_last_name,
                    "invited_role": invitation.invited_role,
                    "status": invitation.status,
                    "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
                    "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
                    "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None,
                }

                if invitation.accepted_user_id:
                    accepted_user = await fetch_user_by_id(self.db, invitation.accepted_user_id)
                    if accepted_user:
                        invitation_data["accepted_user"] = {
                            "user_id": str(accepted_user.user_id),
                            "first_name": accepted_user.first_name,
                            "last_name": accepted_user.last_name,
                            "email": accepted_user.email,
                        }

                invitation_list.append(invitation_data)

            return ResponseBuilder.success(
                "Invitations retrieved successfully",
                {"invitations": invitation_list},
                status_code=200,
            )
        except Exception as e:
            return ResponseBuilder.error(f"Failed to retrieve invitations: {str(e)}", [], status_code=500)

    async def get_invitation_stats(self, user_id: str) -> dict:
        try:
            stats = await get_invitation_stats_db(self.db, user_id)
            return ResponseBuilder.success(
                "Invitation statistics retrieved successfully",
                {"stats": stats},
                status_code=200,
            )
        except Exception as e:
            return ResponseBuilder.error(f"Failed to retrieve invitation statistics: {str(e)}", [], status_code=500)
