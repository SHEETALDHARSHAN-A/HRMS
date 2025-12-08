# app/controllers/invitation_controller.py

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification.invitation_service import InvitationService
from app.utils.standard_response_utils import ResponseBuilder

async def handle_get_my_invitations_controller(request: Request, db: AsyncSession, status_filter: str = None):
    """Get invitations sent by the current user."""
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
        
        service = InvitationService(db)
        result = await service.get_invitations_by_inviter(user_id, status_filter)
        
        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )
        
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )

async def handle_get_invitation_stats_controller(request: Request, db: AsyncSession):
    """Get invitation statistics for the current user."""
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
        
        service = InvitationService(db)
        result = await service.get_invitation_stats(user_id)
        
        return JSONResponse(
            content=result,
            status_code=result.get("status_code", 200)
        )
        
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(f"Internal server error: {str(e)}", [], status_code=500),
            status_code=500
        )