import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from fastapi.responses import JSONResponse

from app.api.v1.authentication_routes import auth_router
import app.controllers.authentication_controller as auth_ctrl
from app.db.connection_manager import get_db
from app.db.redis_manager import get_redis_client


# --- Test App Setup ---
app = FastAPI()
app.include_router(auth_router, prefix="/v1")

# Override DB and Redis dependencies
async def fake_get_db():
    mock_db = AsyncMock()
    try:
        yield mock_db
    finally:
        pass

async def fake_get_redis_client():
    mock_cache = AsyncMock()
    try:
        yield mock_cache
    finally:
        pass

app.dependency_overrides[get_db] = fake_get_db
app.dependency_overrides[get_redis_client] = fake_get_redis_client

client = TestClient(app)


@pytest.mark.asyncio
async def test_send_otp_route_success(monkeypatch):
    # Patch SendOtpService used by the controller
    class FakeSendService:
        def __init__(self, db, cache):
            pass
        async def send_otp(self, user_data):
            return {"success": True, "message": "OTP sent", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, "SendOtpService", FakeSendService)

    resp = client.post("/v1/auth/send-otp", json={"email": "test+send@example.com"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is True
    assert "OTP" in data["message"]


@pytest.mark.asyncio
async def test_resend_otp_route_success(monkeypatch):
    class FakeResendService:
        # Service in controller may be instantiated with (cache, db) or (cache)
        def __init__(self, cache, db=None):
            pass
        async def resend_otp(self, user_data):
            return {"success": True, "message": "OTP resent", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, "ResendOtpService", FakeResendService)

    resp = client.post("/v1/auth/resend-otp", json={"email": "test+resend@example.com"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is True
    assert "resent" in data["message"].lower()


@pytest.mark.asyncio
async def test_verify_otp_route_success(monkeypatch):
    # Return a JSONResponse directly as VerifyOtpService is expected to return a JSONResponse
    class FakeVerifyService:
        def __init__(self, db, cache):
            pass
        async def verify_otp(self, data, response):
            return JSONResponse(content={"success": True, "message": "Verified"}, status_code=status.HTTP_200_OK)

    monkeypatch.setattr(auth_ctrl, 'VerifyOtpService', FakeVerifyService)

    resp = client.post("/v1/auth/verify-otp", json={"email": "test+verify@example.com", "otp": "123456"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_check_email_status_route(monkeypatch):
    # Patch CheckUserExistenceService to return available status
    class FakeCheckService:
        def __init__(self, db):
            pass
        async def check_email_status(self, email):
            return {"success": True, "message": "Email available", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'CheckUserExistenceService', FakeCheckService)

    resp = client.get("/v1/auth/check-email-status?email=test@example.com")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is True

    # Simulate email already exists returning 409
    class FakeCheckServiceConflict(FakeCheckService):
        async def check_email_status(self, email):
            return {"success": False, "message": "Email exists", "status_code": status.HTTP_409_CONFLICT}

    monkeypatch.setattr(auth_ctrl, 'CheckUserExistenceService', FakeCheckServiceConflict)
    resp2 = client.get("/v1/auth/check-email-status?email=test@example.com")
    assert resp2.status_code == status.HTTP_409_CONFLICT
    assert resp2.json()["success"] is False


@pytest.mark.asyncio
async def test_debug_list_emails_route_outputs_emails(monkeypatch):
    # Fake db execute to return rows via fetchall
    class FakeResult:
        def __init__(self, rows):
            self._rows = rows
        def fetchall(self):
            return self._rows

    class FakeDB:
        async def execute(self, q, *a, **kw):
            return FakeResult([("a@example.com", "HR", "11111111-1111-1111-1111-111111111111")])

    # Replace dependency
    async def fake_get_db_override():
        try:
            yield FakeDB()
        finally:
            pass

    app.dependency_overrides[get_db] = fake_get_db_override

    resp = client.get("/v1/auth/debug-list-emails")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["users"][0]["email"] == "a@example.com"


# End of tests
