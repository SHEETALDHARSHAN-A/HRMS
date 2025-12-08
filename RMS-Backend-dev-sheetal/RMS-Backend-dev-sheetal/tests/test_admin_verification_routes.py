import json
import pytest
from unittest.mock import AsyncMock
from fastapi import status, HTTPException
import app.controllers.authentication_controller as auth_ctrl
from app.services.admin_service.update_admin_service import UpdateAdminService


@pytest.mark.asyncio
async def test_verify_name_update_success_redirect(client, monkeypatch):
    # Make verify_name_update return success
    async def fake_verify_name(token, user_id):
        return {"success": True}

    monkeypatch.setattr(UpdateAdminService, 'verify_name_update', staticmethod(fake_verify_name))
    resp = client.get("/v1/admins/verify-name-update?user_id=123&token=tok", headers={"x-test-user": "{}"})
    # TestClient follows redirects to the dummy endpoint; ensure redirect occurred
    assert resp.status_code == 200
    assert resp.history != []


@pytest.mark.asyncio
async def test_verify_name_update_failure_redirect(monkeypatch, client):
    async def fake_verify_name(token, user_id):
        return {"success": False, "message": "Bad token"}

    monkeypatch.setattr(UpdateAdminService, 'verify_name_update', staticmethod(fake_verify_name))
    resp = client.get("/v1/admins/verify-name-update?user_id=123&token=tok")
    assert resp.status_code == 200
    # Ensure the redirect leads to processing endpoint
    assert resp.json()["success"] is True or resp.history != []


@pytest.mark.asyncio
async def test_confirm_phone_update_success_redirect(monkeypatch, client):
    async def fake_verify_phone(token, user_id):
        return {"success": True}

    monkeypatch.setattr(UpdateAdminService, 'verify_phone_update', staticmethod(fake_verify_phone))
    resp = client.get("/v1/admins/confirm-phone-update?token=tok&user_id=123")
    assert resp.status_code == 200
    assert resp.history != []


@pytest.mark.asyncio
async def test_approve_email_update_redirect(monkeypatch, client):
    monkeypatch.setattr(UpdateAdminService, 'approve_email_update', staticmethod(lambda token, uid: {"success": True, "data": {"new_email": "n@e.com"}}))
    resp = client.get("/v1/admins/approve-email-update?token=abc&user_id=123")
    assert resp.status_code == 200
    assert resp.history != []


@pytest.mark.asyncio
async def test_verify_email_update_post_and_get(monkeypatch, client):
    # GET verify
    class FakeUpdateServiceGET:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateServiceGET)
    resp = client.get("/v1/admins/verify-email-update?user_id=123&token=tok&new_email=a@example.com")
    assert resp.status_code == 200

    # POST verify
    class FakeUpdateServicePOST:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True, "message": "OK", "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateServicePOST)
    resp2 = client.post("/v1/admins/verify-email-update", json={"user_id": "123", "token": "tok", "new_email": "a@example.com"})
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_verify_name_update_missing_params(client):
    # Missing query params should return 422
    resp = client.get("/v1/admins/verify-name-update")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_confirm_phone_update_missing_params(client):
    resp = client.get("/v1/admins/confirm-phone-update")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_approve_email_update_missing_params(client):
    resp = client.get("/v1/admins/approve-email-update")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_name_update_service_error(monkeypatch, client):
    class FakeService:
        def __init__(self, db, cache):
            pass
        async def verify_name_update(self, token, user_id):
            raise HTTPException(status_code=404, detail="Not found")

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    resp = client.get("/v1/admins/verify-name-update?user_id=123&token=tok")
    # Route returns a redirect to the frontend with an error when the service raises HTTPException
    assert resp.status_code == 200
    assert resp.history != []
    location = resp.history[-1].headers.get('location', '')
    assert 'status=error' in location


@pytest.mark.asyncio
async def test_confirm_phone_update_service_error(monkeypatch, client):
    class FakeService:
        def __init__(self, db, cache):
            pass
        async def verify_phone_update(self, token, user_id):
            raise HTTPException(status_code=401, detail="Unauthorized")

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    resp = client.get("/v1/admins/confirm-phone-update?token=tok&user_id=123")
    assert resp.status_code == 200
    assert resp.history != []
    location = resp.history[-1].headers.get('location', '')
    assert 'status=error' in location


@pytest.mark.asyncio
async def test_approve_email_update_service_error(monkeypatch, client):
    class FakeService:
        def __init__(self, db, cache):
            pass
        async def approve_email_update(self, token, uid):
            raise HTTPException(status_code=400, detail="Bad request")

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    resp = client.get("/v1/admins/approve-email-update?token=abc&user_id=123")
    assert resp.status_code == 200
    assert resp.history != []
    location = resp.history[-1].headers.get('location', '')
    assert 'status=email_transfer_error' in location


@pytest.mark.asyncio
async def test_verify_email_update_get_service_error(monkeypatch, client):
    # Simulate service raising HTTPException
    class FakeServiceGET:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            raise HTTPException(status_code=404, detail="Not found")

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceGET)
    resp = client.get("/v1/admins/verify-email-update?user_id=123&token=tok&new_email=a@example.com")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_verify_email_update_post_service_error(monkeypatch, client):
    class FakeServicePOST:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            raise HTTPException(status_code=400, detail="Bad request")

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServicePOST)
    resp = client.post("/v1/admins/verify-email-update", json={"user_id": "123", "token": "tok", "new_email": "a@example.com"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_complete_email_update_status_redirect(monkeypatch, client):
    # Mock UpdateAdminService.verify_email_update to indicate success
    class FakeUpdateEmailService:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True, "data": {}, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateEmailService)
    # request to complete-email-update-status should redirect to /auth with success
    resp = client.get("/v1/admins/complete-email-update-status?token=tok&user_id=123&new_email=a@example.com")
    assert resp.status_code == 200
    assert resp.history != []

    @pytest.mark.asyncio
    async def test_complete_email_update_status_missing_params(client):
        resp = client.get("/v1/admins/complete-email-update-status")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_complete_email_update_status_service_exception_with_redirect(monkeypatch, client):
        # Simulate service raising a generic exception; route should redirect to provided redirect_to
        class FakeServiceFail:
            def __init__(self, db, cache):
                pass
            async def verify_email_update(self, payload):
                raise Exception("boom")

        monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceFail)
        redirect_to = "http://testserver/custom"
        resp = client.get(f"/v1/admins/complete-email-update-status?token=tok&user_id=123&new_email=a@example.com&redirect_to={redirect_to}")
        # TestClient will follow redirect; final status should be 200 but history shows redirect
        assert resp.history != []
        # Check the final redirect happened to the redirect_to
        assert redirect_to in resp.history[-1].headers.get('location', '')

    @pytest.mark.asyncio
    async def test_complete_email_update_status_service_exception_no_redirect(client, monkeypatch):
        class FakeServiceFail:
            def __init__(self, db, cache):
                pass
            async def verify_email_update(self, payload):
                raise Exception("boom2")

        monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceFail)
        resp = client.get(f"/v1/admins/complete-email-update-status?token=tok&user_id=123&new_email=a@example.com")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
