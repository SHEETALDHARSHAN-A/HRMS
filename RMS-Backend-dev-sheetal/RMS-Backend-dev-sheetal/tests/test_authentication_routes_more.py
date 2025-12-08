import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
from types import SimpleNamespace
from jose import JWTError, ExpiredSignatureError

from app.api.v1.authentication_routes import auth_router, admin_router
import app.controllers.authentication_controller as auth_ctrl
from app.db.connection_manager import get_db
from app.db.redis_manager import get_redis_client


# --- Setup test app ---
app = FastAPI()
app.include_router(auth_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")

# Test middleware to inject user into request.state for endpoints that rely on request.state.user
@app.middleware("http")
async def _inject_test_user(request, call_next):
    import json
    test_user_json = request.headers.get("x-test-user")
    if test_user_json:
        try:
            request.state.user = json.loads(test_user_json)
        except Exception:
            request.state.user = None
    else:
        request.state.user = None
    return await call_next(request)

# Override dependencies
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

# Ensure redirect targets return success within TestClient by pointing frontend to testserver
auth_ctrl.settings.frontend_url = "http://testserver"

# Add dummy frontend endpoints to catch redirects during tests
@app.get("/verification/processing")
def _dummy_verification_processing():
    return {"success": True}

@app.get("/auth")
def _dummy_auth_route():
    return {"success": True}


# Utility to create a fake request with a specific user payload
def make_fake_request(user_payload=None):
    req = MagicMock()
    req.state = MagicMock()
    req.state.user = user_payload
    return req


@pytest.mark.asyncio
async def test_check_cookie_no_token_returns_401(monkeypatch):
    # No cookies: should return 401
    resp = client.get("/v1/auth/check-cookie")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_check_cookie_valid_token_returns_user(monkeypatch):
    # Provide cookie and monkeypatch jwt.decode to return payload
    payload = {"sub": "user-1", "role": "ADMIN", "fn": "Jane", "ln": "Doe"}

    def fake_decode(token, key, algorithms):
        return payload

    monkeypatch.setattr(auth_ctrl, 'jwt', MagicMock(decode=fake_decode))

    # Set a cookie
    client.cookies.set("access_token", "token")

    resp = client.get("/v1/auth/check-cookie")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_check_cookie_jwt_expired_and_invalid(monkeypatch):
    # ExpiredSignatureError should return 401
    def expired_decode(token, key, algorithms):
        raise ExpiredSignatureError("expired")

    monkeypatch.setattr(auth_ctrl, 'jwt', MagicMock(decode=expired_decode))
    client.cookies.set("access_token", "expired-token")
    resp = client.get("/v1/auth/check-cookie")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # JWTError should return 403
    def invalid_decode(token, key, algorithms):
        raise JWTError("invalid")

    monkeypatch.setattr(auth_ctrl, 'jwt', MagicMock(decode=invalid_decode))
    client.cookies.set("access_token", "bad-token")
    resp2 = client.get("/v1/auth/check-cookie")
    assert resp2.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_logout_revokes_and_deletes_cookies(monkeypatch):
    # monkeypatch jwt.decode to return payload with jti and exp
    payload = {"jti": "token-id", "exp": 9999999999}

    def fake_decode(token, key, algorithms):
        return payload

    monkeypatch.setattr(auth_ctrl, 'jwt', MagicMock(decode=fake_decode))

    # Monkeypatch add_jti_to_blocklist to return coroutine
    async def fake_add_jti(jti, cache, ttl):
        return True

    monkeypatch.setattr(auth_ctrl, 'add_jti_to_blocklist', fake_add_jti)

    # Set cookies
    client.cookies.set("access_token", "access-token")
    client.cookies.set("refresh_token", "refresh-token")

    resp = client.get("/v1/auth/logout")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_invite_admin_route_role_permissions(monkeypatch):
    # Create fake request with user payload as SUPER_ADMIN
    admin_user = {"role": "SUPER_ADMIN", "sub": "u1"}
    import json
    header_val = json.dumps(admin_user)
    class FakeInviteService:
        def __init__(self, db, cache):
            pass
        async def generate_admin_invite(self, data, caller_user_id):
            return {"success": True, "message": "Invite sent", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'InviteAdminService', FakeInviteService)

    resp = client.post("/v1/admins/invite", json={"email": "a@b.com", "first_name": "A", "role": "HR"}, headers={"x-test-user": header_val})
    assert resp.status_code == status.HTTP_200_OK

    # Now attempt HR inviting ADMIN (should be forbidden)
    hr_user = {"role": "HR", "sub": "u2"}
    header_val2 = json.dumps(hr_user)
    resp2 = client.post("/v1/admins/invite", json={"email": "a@b.com", "first_name": "A", "role": "ADMIN"}, headers={"x-test-user": header_val2})
    assert resp2.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_complete_admin_setup_route(monkeypatch):
    # Simple test: service returns created job
    class FakeCompleteService:
        def __init__(self, db, cache):
            pass
        async def complete_admin_setup(self, token, response):
            return {"success": True, "message": "Created", "status_code": status.HTTP_201_CREATED}

    monkeypatch.setattr(auth_ctrl, 'CompleteAdminSetupService', FakeCompleteService)

    resp = client.post("/v1/admins/complete-admin-setup?token=abc")
    # Endpoint returns JSONResponse with 201
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_list_all_admins_route_and_delete_batch(monkeypatch):
    # list-all requires request.state.user role, set to SUPER_ADMIN
    import json
    header_val = json.dumps({"role": "SUPER_ADMIN"})
    class FakeGetAll:
            def __init__(self, db):
                pass
            async def get_all_admins(self, caller_role):
                return {"success": True, "message": "OK", "data": {"admins": []}, "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'GetAllAdminsService', FakeGetAll)
    resp = client.get("/v1/admins/list-all", headers={"x-test-user": header_val})
    assert resp.status_code == status.HTTP_200_OK

    # delete-batch
    header_val = json.dumps({"role": "SUPER_ADMIN", "sub": "u1"})
    class FakeDeleteBatch:
            def __init__(self, db):
                pass
            async def delete_admins(self, user_data, caller_role, caller_id):
                return {"success": True, "message": "Deleted", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'DeleteAdminsBatchService', FakeDeleteBatch)
    resp2 = client.request("DELETE", "/v1/admins/delete-batch", json={"user_ids": ["u2"]}, headers={"x-test-user": header_val})
    assert resp2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_admin_by_id_and_search(monkeypatch):
    class FakeGetById:
        def __init__(self, db):
            pass
        async def get_admin_details(self, admin_id):
            return {"success": True, "message": "OK", "data": {"admin": {"user_id": admin_id}}, "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'GetAdminByIdService', FakeGetById)
    resp = client.get("/v1/admins/get/123", headers={"x-test-user": "{}"})
    assert resp.status_code == status.HTTP_200_OK

    # search_admins uses repository search_admins; patch DB repo function
    with patch("app.db.repository.user_repository.search_admins") as mock_search:
        mock_search.return_value = [{"user_id": "id1"}]
        resp2 = client.get("/v1/admins/search?q=test")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.json()["success"] is True


@pytest.mark.asyncio
async def test_update_admin_route(monkeypatch):
    header_val = json.dumps({"role": "SUPER_ADMIN", "sub": "u1"})
    # Using middleware header to set request.state.user
    class FakeUpdateAdmin:
            def __init__(self, db, cache):
                pass
            async def update_admin_details(self, admin_id, user_data, caller_role, caller_id):
                return {"success": True, "message": "Updated", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateAdmin)
    resp = client.put("/v1/admins/update/123", json={"first_name": "New"}, headers={"x-test-user": header_val})
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_verify_name_and_phone_redirects(monkeypatch):
    # verify-name-update -> Redirect
    def fake_verify_name(token, user_id):
        return {"success": True}

    async def fake_verify_name(token, user_id):
        return {"success": True}
    monkeypatch.setattr(auth_ctrl.UpdateAdminService, 'verify_name_update', staticmethod(fake_verify_name))

    # Call route; it expects token and user_id querystring. If no user is required it's public, otherwise pass a test user header
    resp = client.get("/v1/admins/verify-name-update?user_id=123&token=tok", headers={"x-test-user": "{}"})
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_200_OK)

    # confirm-phone-update
    async def fake_verify_phone(token, user_id):
        return {"success": True}
    monkeypatch.setattr(auth_ctrl.UpdateAdminService, 'verify_phone_update', staticmethod(fake_verify_phone))
    resp_phone = client.get("/v1/admins/confirm-phone-update?token=tok&user_id=123")
    assert resp_phone.status_code in (status.HTTP_302_FOUND, status.HTTP_200_OK)


@pytest.mark.asyncio
async def test_verify_email_update_endpoints(monkeypatch):
    # GET verify: uses handle_verify_admin_email_update_controller directly, which we patch
    class FakeUpdateEmailServiceGET:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateEmailServiceGET)
    resp = client.get("/v1/admins/verify-email-update?user_id=123&token=tok&new_email=a@example.com")
    assert resp.status_code == status.HTTP_200_OK

    # POST verify email update: patch UpdateAdminService.verify_email_update
    class FakeUpdateEmailService:
        def __init__(self, db, cache):
            pass
        async def verify_email_update(self, payload):
            return {"success": True, "message": "OK", "status_code": status.HTTP_200_OK}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateEmailService)
    resp2 = client.post("/v1/admins/verify-email-update", json={"user_id": "123", "token": "tok", "new_email": "a@example.com"})
    assert resp2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_approve_email_update_redirect(monkeypatch):
    # Return successful approval
    monkeypatch.setattr(auth_ctrl.UpdateAdminService, 'approve_email_update', staticmethod(lambda token, uid: {"success": True, "data": {"new_email": "n@e.com"}}))
    resp = client.get("/v1/admins/approve-email-update?token=abc&user_id=123")
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_200_OK)


# End of tests
