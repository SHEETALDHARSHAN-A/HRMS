import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from types import SimpleNamespace

from app.controllers.invitation_controller import handle_get_my_invitations_controller
from app.controllers.agent_config_routes import update_agent_config_route
from app.schemas.config_request import AgentConfigUpdateRequest
from app.controllers.authentication_controller import handle_invite_admin_controller
from app.schemas.authentication_request import AdminInviteRequest

@pytest.mark.asyncio
async def test_invitation_controller_unauth():
    # Request without user state
    req = SimpleNamespace(state=SimpleNamespace())
    res = await handle_get_my_invitations_controller(req, None)
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_invitation_controller_success(fake_db):
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "u1"}))
    
    with patch("app.controllers.invitation_controller.InvitationService") as MockService:
        MockService.return_value.get_invitations_by_inviter = AsyncMock(return_value={"status_code": 200})
        res = await handle_get_my_invitations_controller(req, fake_db)
        assert res.status_code == 200

@pytest.mark.asyncio
async def test_invite_admin_controller_role_logic(fake_db, fake_cache):
    # Test HR inviting Admin (Forbidden)
    req = SimpleNamespace(state=SimpleNamespace(user={"role": "HR", "sub": "u1"}))
    payload = AdminInviteRequest(email="a@a.com", role="ADMIN", first_name="A", last_name="B")
    
    res = await handle_invite_admin_controller(payload, fake_db, fake_cache, req)
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_update_agent_config_route_validation():
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "u1"}))
    payload = AgentConfigUpdateRequest(agentRounds=[])
    
    # Invalid UUID
    with pytest.raises(Exception) as exc: # Route raises HTTPException directly
        await update_agent_config_route("invalid-uuid", req, payload, None)
    assert exc.value.status_code == 400