# app/api/v1/invitation_routes.py

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request, Query

from app.db.connection_manager import get_db
from app.controllers.invitation_controller import (
    handle_get_my_invitations_controller,
    handle_get_invitation_stats_controller
)

invitation_router = APIRouter(prefix="/invitations", tags=["Invitations"])

@invitation_router.get("/my-invitations", summary="Get my sent invitations")
async def get_my_invitations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    status: str = Query(None, description="Filter by status: PENDING, ACCEPTED, EXPIRED, REVOKED")
):
    """Get all invitations sent by the current user."""
    return await handle_get_my_invitations_controller(request, db, status)

@invitation_router.get("/stats", summary="Get invitation statistics")
async def get_invitation_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get invitation statistics for the current user."""
    return await handle_get_invitation_stats_controller(request, db)