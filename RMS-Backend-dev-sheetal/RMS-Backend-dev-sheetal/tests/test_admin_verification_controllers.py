import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException
import app.controllers.authentication_controller as auth_ctrl
from app.services.admin_service.update_admin_service import UpdateAdminService
from fastapi.responses import RedirectResponse, JSONResponse


@pytest.mark.asyncio
async def test_handle_verify_admin_name_update_controller_success(monkeypatch):
    async def fake_verify(token, user_id):
        return {"success": True}

    monkeypatch.setattr(UpdateAdminService, 'verify_name_update', staticmethod(fake_verify))
    resp = await auth_ctrl.handle_verify_admin_name_update_controller('token', 'uid', db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 302
    assert "verification/processing" in resp.headers.get('location', '')


@pytest.mark.asyncio
async def test_handle_verify_admin_name_update_controller_failure(monkeypatch):
    async def fake_verify(token, user_id):
        return {"success": False, "message": "bad"}

    monkeypatch.setattr(UpdateAdminService, 'verify_name_update', staticmethod(fake_verify))
    resp = await auth_ctrl.handle_verify_admin_name_update_controller('token', 'uid', db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, RedirectResponse)
    assert "status=error" in resp.headers.get('location', '')


@pytest.mark.asyncio
async def test_handle_verify_admin_name_update_controller_exception(monkeypatch):
    async def fake_verify(token, user_id):
        raise HTTPException(status_code=400, detail="Bad token")

    monkeypatch.setattr(UpdateAdminService, 'verify_name_update', staticmethod(fake_verify))
    resp = await auth_ctrl.handle_verify_admin_name_update_controller('token', 'uid', db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, RedirectResponse)
    assert "status=error" in resp.headers.get('location', '')


@pytest.mark.asyncio
async def test_handle_verify_admin_phone_update_controller_success(monkeypatch):
    async def fake_verify(token, user_id):
        return {"success": True}

    monkeypatch.setattr(UpdateAdminService, 'verify_phone_update', staticmethod(fake_verify))
    resp = await auth_ctrl.handle_verify_admin_phone_update_controller('token', 'uid', db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 302


@pytest.mark.asyncio
async def test_handle_approve_email_update_controller_success(monkeypatch):
    async def fake_approve(token, user_id):
        return {"success": True, "data": {"new_email": "n@e.com"}}

    monkeypatch.setattr(UpdateAdminService, 'approve_email_update', staticmethod(fake_approve))
    resp = await auth_ctrl.handle_approve_email_update_controller('token', 'uid', db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, RedirectResponse)
    assert "status=email_transfer_approved" in resp.headers.get('location', '')


@pytest.mark.asyncio
async def test_handle_verify_admin_email_update_controller_returns_json(monkeypatch):
    class FakeService:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    resp = await auth_ctrl.handle_verify_admin_email_update_controller(AsyncMock(), db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_handle_complete_email_update_controller_success(monkeypatch):
    class FakeService:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    resp = await auth_ctrl.handle_complete_email_update_controller('token', 'uid', 'a@example.com', db=AsyncMock(), cache=AsyncMock())
    assert isinstance(resp, RedirectResponse)
    assert "status=email_updated" in resp.headers.get('location', '')
