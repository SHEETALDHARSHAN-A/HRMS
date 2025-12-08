from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository.notification_repository import (
    fetch_notifications,
    fetch_user_by_id,
    mark_notification_read_db,
    mark_all_notifications_read_db,
    get_unread_count_db,
    delete_notification_db,
)
from app.utils.standard_response_utils import ResponseBuilder


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_notifications(self, user_id: str, unread_only: bool = False, limit: int = 50) -> dict:
        try:
            notifications = await fetch_notifications(self.db, user_id, unread_only, limit)
            notification_list = []
            for notification in notifications:
                notification_data = {
                    "notification_id": str(notification.notification_id),
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat() if notification.created_at else None,
                    "read_at": notification.read_at.isoformat() if notification.read_at else None,
                }
                if notification.related_invitation_id:
                    notification_data["related_invitation_id"] = str(notification.related_invitation_id)
                if notification.related_user_id:
                    related_user = await fetch_user_by_id(self.db, notification.related_user_id)
                    if related_user:
                        notification_data["related_user"] = {
                            "user_id": str(related_user.user_id),
                            "first_name": related_user.first_name,
                            "last_name": related_user.last_name,
                            "email": related_user.email,
                            "role": related_user.role,
                        }
                notification_list.append(notification_data)

            return ResponseBuilder.success(
                "Notifications retrieved successfully",
                {"notifications": notification_list},
                status_code=200,
            )
        except Exception as e:
            return ResponseBuilder.error(f"Failed to retrieve notifications: {str(e)}", [], status_code=500)

    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> dict:
        try:
            ok = await mark_notification_read_db(self.db, notification_id, user_id)
            if not ok:
                return ResponseBuilder.error("Notification not found", [], status_code=404)
            return ResponseBuilder.success("Notification marked as read", {"notification_id": notification_id}, status_code=200)
        except Exception as e:
            return ResponseBuilder.error(f"Failed to mark notification as read: {str(e)}", [], status_code=500)

    async def mark_all_notifications_as_read(self, user_id: str) -> dict:
        try:
            updated_count = await mark_all_notifications_read_db(self.db, user_id)
            return ResponseBuilder.success(f"Marked {updated_count} notifications as read", {"updated_count": updated_count}, status_code=200)
        except Exception as e:
            return ResponseBuilder.error(f"Failed to mark all notifications as read: {str(e)}", [], status_code=500)

    async def get_unread_count(self, user_id: str) -> dict:
        try:
            count = await get_unread_count_db(self.db, user_id)
            return ResponseBuilder.success("Unread count retrieved successfully", {"unread_count": count}, status_code=200)
        except Exception as e:
            return ResponseBuilder.error(f"Failed to get unread count: {str(e)}", [], status_code=500)

    async def delete_notification(self, notification_id: str, user_id: str) -> dict:
        try:
            ok = await delete_notification_db(self.db, notification_id, user_id)
            if not ok:
                return ResponseBuilder.error("Notification not found", [], status_code=404)
            return ResponseBuilder.success("Notification deleted", {"notification_id": notification_id}, status_code=200)
        except Exception as e:
            return ResponseBuilder.error(f"Failed to delete notification: {str(e)}", [], status_code=500)
