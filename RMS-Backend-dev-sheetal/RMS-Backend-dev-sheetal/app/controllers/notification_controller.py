# app/controllers/notification_controller.py

from fastapi import Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.standard_response_utils import ResponseBuilder
from app.services.notification.notification_service import NotificationService

async def handle_get_notifications_controller(
    request: Request, 
    db: AsyncSession, 
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100)
):
    """Get notifications for the current user."""
    try:
        # Get user ID from JWT token
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=401),
                status_code=401
            )
        
        # Get user ID from JWT token (check both 'user_id' and standard 'sub' field)
        user_id = user_payload.get("user_id") or user_payload.get("sub")
        if not user_id:
            return JSONResponse(
                content=ResponseBuilder.error("User ID not found in token", [], status_code=401),
                status_code=401
            )
        
        service = NotificationService(db)
        result = await service.get_notifications(user_id, unread_only, limit)
        
        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )
        
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )

async def handle_mark_notification_read_controller(request: Request, db: AsyncSession, notification_id: str):
    """Mark a specific notification as read."""
    try:
        # Get user ID from JWT token
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=401),
                status_code=401
            )
        
        # Get user ID from JWT token (check both 'user_id' and standard 'sub' field)
        user_id = user_payload.get("user_id") or user_payload.get("sub")
        if not user_id:
            return JSONResponse(
                content=ResponseBuilder.error("User ID not found in token", [], status_code=401),
                status_code=401
            )
        
        service = NotificationService(db)
        result = await service.mark_notification_as_read(notification_id, user_id)
        
        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )
        
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )

async def handle_mark_all_notifications_read_controller(request: Request, db: AsyncSession):
    """Mark all notifications as read for the current user."""
    try:
        # Get user ID from JWT token
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=401),
                status_code=401
            )
        
        # Get user ID from JWT token (check both 'user_id' and standard 'sub' field)
        user_id = user_payload.get("user_id") or user_payload.get("sub")
        if not user_id:
            return JSONResponse(
                content=ResponseBuilder.error("User ID not found in token", [], status_code=401),
                status_code=401
            )
        
        service = NotificationService(db)
        result = await service.mark_all_notifications_as_read(user_id)
        
        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )
        
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )

async def handle_get_unread_count_controller(request: Request, db: AsyncSession):
    """Get count of unread notifications for the current user."""
    try:
        # Get user ID from JWT token
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=401),
                status_code=401
            )
        
        # Get user ID from JWT token (check both 'user_id' and standard 'sub' field)
        user_id = user_payload.get("user_id") or user_payload.get("sub")
        if not user_id:
            return JSONResponse(
                content=ResponseBuilder.error("User ID not found in token", [], status_code=401),
                status_code=401
            )
        
        service = NotificationService(db)
        result = await service.get_unread_count(user_id)
        
        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )
        
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )


async def handle_delete_notification_controller(request: Request, db: AsyncSession, notification_id: str):
    """Delete a specific notification for the current user."""
    try:
        # Get user ID from JWT token
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=401),
                status_code=401
            )

        user_id = user_payload.get("user_id") or user_payload.get("sub")
        if not user_id:
            return JSONResponse(
                content=ResponseBuilder.error("User ID not found in token", [], status_code=401),
                status_code=401
            )

        service = NotificationService(db)
        result = await service.delete_notification(notification_id, user_id)

        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )

    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )