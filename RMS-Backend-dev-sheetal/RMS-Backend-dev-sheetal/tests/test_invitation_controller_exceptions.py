import pytest
import json
from types import SimpleNamespace

import app.controllers.invitation_controller as inv_ctrl


@pytest.mark.asyncio
async def test_get_my_invitations_missing_user_returns_401():
    req = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await inv_ctrl.handle_get_my_invitations_controller(req, db=None)
    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "Authentication required" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_get_my_invitations_missing_user_id_returns_401():
    # Provide a truthy user payload without 'user_id' or 'sub' to trigger the "User ID not found" branch
    req = SimpleNamespace(state=SimpleNamespace(user={"foo": "bar"}))
    resp = await inv_ctrl.handle_get_my_invitations_controller(req, db=None)
    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "User ID not found in token" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_get_my_invitations_service_exception_returns_500(monkeypatch):
    class BadService:
        def __init__(self, db):
            pass

        async def get_invitations_by_inviter(self, user_id, status_filter):
            raise Exception("inv-svc-fail")

    monkeypatch.setattr(inv_ctrl, "InvitationService", BadService)
    req = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1"}))
    resp = await inv_ctrl.handle_get_my_invitations_controller(req, db=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "inv-svc-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_get_invitation_stats_missing_user_and_missing_user_id_and_service_error(monkeypatch):
    # missing user -> 401
    req_none = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await inv_ctrl.handle_get_invitation_stats_controller(req_none, db=None)
    assert resp.status_code == 401

    # missing user_id -> 401
    req = SimpleNamespace(state=SimpleNamespace(user={}))
    resp2 = await inv_ctrl.handle_get_invitation_stats_controller(req, db=None)
    assert resp2.status_code == 401

    # service raises -> 500
    class BadService2:
        def __init__(self, db):
            pass

        async def get_invitation_stats(self, user_id):
            raise Exception("stats-fail")

    monkeypatch.setattr(inv_ctrl, "InvitationService", BadService2)
    req_ok = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u2"}))
    resp3 = await inv_ctrl.handle_get_invitation_stats_controller(req_ok, db=None)
    assert resp3.status_code == 500
    body = json.loads(resp3.body)
    assert body.get("success") is False
    assert "stats-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_get_invitation_stats_success_returns_service_result(monkeypatch):
    class GoodService:
        def __init__(self, db):
            pass

        async def get_invitation_stats(self, user_id):
            return {"success": True, "data": {"sent": 3}, "status_code": 200}

    monkeypatch.setattr(inv_ctrl, "InvitationService", GoodService)
    req = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u100"}))
    resp = await inv_ctrl.handle_get_invitation_stats_controller(req, db=None)
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("success") is True
    assert body.get("data", {}).get("sent") == 3


@pytest.mark.asyncio
async def test_get_my_invitations_user_id_not_found_exact_message():
    # Provide truthy user payload without id to hit the branch and assert exact message
    req = SimpleNamespace(state=SimpleNamespace(user={"some": "val"}))
    resp = await inv_ctrl.handle_get_my_invitations_controller(req, db=None)
    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body.get("message") == "User ID not found in token"


@pytest.mark.asyncio
async def test_get_invitation_stats_user_id_not_found_exact_message():
    req = SimpleNamespace(state=SimpleNamespace(user={"x": "y"}))
    resp = await inv_ctrl.handle_get_invitation_stats_controller(req, db=None)
    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body.get("message") == "User ID not found in token"
