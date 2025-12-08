# app/api/v1/notification_routes.py

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request, Query, Path

from app.db.connection_manager import get_db
from app.controllers.notification_controller import (
    handle_get_notifications_controller,
    handle_mark_notification_read_controller,
    handle_mark_all_notifications_read_controller,
    handle_get_unread_count_controller
)
from app.controllers.notification_controller import (
    handle_delete_notification_controller,
)

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notification_router.get("/", summary="Get notifications")
async def get_notifications(
    request: Request,
    db: AsyncSession = Depends(get_db),
    unread_only: bool = Query(False, description="Get only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications to return")
):
    """Get notifications for the current user."""
    return await handle_get_notifications_controller(request, db, unread_only, limit)

@notification_router.get("/unread-count", summary="Get unread notification count")
async def get_unread_count(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications for the current user."""
    return await handle_get_unread_count_controller(request, db)

@notification_router.put("/{notification_id}/mark-read", summary="Mark notification as read")
async def mark_notification_read(
    notification_id: str = Path(..., description="ID of the notification to mark as read"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Mark a specific notification as read."""
    return await handle_mark_notification_read_controller(request, db, notification_id)

@notification_router.put("/mark-all-read", summary="Mark all notifications as read")
async def mark_all_notifications_read(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for the current user."""
    return await handle_mark_all_notifications_read_controller(request, db)


@notification_router.delete("/{notification_id}", summary="Delete a notification")
async def delete_notification(
    notification_id: str = Path(..., description="ID of the notification to delete"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific notification for the current user."""
    return await handle_delete_notification_controller(request, db, notification_id)