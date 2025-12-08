import pytest
import json
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta

from unittest.mock import AsyncMock

import app.controllers.authentication_controller as auth_ctrl
from app.controllers.authentication_controller import (
    handle_check_cookie_controller,
    handle_logout_controller,
    handle_invite_admin_controller,
    handle_get_all_admins_controller,
    handle_delete_admins_batch_controller,
    handle_get_admin_by_id_controller,
)

from app.schemas.authentication_request import AdminInviteRequest, DeleteAdminsBatchRequest
from fastapi import Response


def _resp_json(resp):
    """Return parsed JSON for a starlette.responses.JSONResponse-like object."""
    # JSONResponse produced by controller is not the TestClient response; it stores bytes in .body
    if hasattr(resp, "body"):
        raw = resp.body
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)
    # Fallback for objects that expose .media
    if hasattr(resp, "media"):
        return resp.media
    # Last resort: try attribute access
    if hasattr(resp, "json"):
        return resp.json()
    raise RuntimeError("Unable to parse JSON from response object")


@pytest.mark.asyncio
async def test_handle_check_cookie_returns_user_when_token_valid(monkeypatch):
    # Arrange: fake JWT decode to return payload
    payload = {"sub": "user-1", "role": "ADMIN", "fn": "Jane", "ln": "Doe"}

    async_db = AsyncMock()

    def fake_decode(token, key, algorithms):
        return payload

    monkeypatch.setattr(auth_ctrl, 'jwt', SimpleNamespace(decode=fake_decode))

    # Patch get_user_by_id to ensure not called (names present in token)
    monkeypatch.setattr(auth_ctrl, 'get_user_by_id', AsyncMock())

    req = SimpleNamespace()
    req.cookies = {"access_token": "tok"}

    # Act
    resp = await handle_check_cookie_controller(req, async_db)

    # Assert
    assert resp.status_code == 200
    data = _resp_json(resp)
    assert data["success"] is True
    assert data["data"]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_handle_logout_controller_revokes_tokens_and_deletes_cookies(monkeypatch):
    # Arrange: jwt.decode returns payloads with jti and exp in future
    future = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    payload = {"jti": "jti-1", "exp": future}

    def fake_decode(token, key, algorithms):
        return payload

    monkeypatch.setattr(auth_ctrl, 'jwt', SimpleNamespace(decode=fake_decode))

    # Patch add_jti_to_blocklist to be async
    async def fake_add_jti(jti, cache, ttl):
        return True

    monkeypatch.setattr(auth_ctrl, 'add_jti_to_blocklist', fake_add_jti)

    response = Response()
    req = SimpleNamespace()
    req.cookies = {"access_token": "a", "refresh_token": "r"}

    cache = AsyncMock()

    # Act
    resp = await handle_logout_controller(response, req, cache)

    # Assert
    assert resp.status_code == 200
    assert _resp_json(resp)["success"] is True


@pytest.mark.asyncio
async def test_handle_invite_admin_controller_permissions_and_success(monkeypatch):
    db = AsyncMock()
    cache = AsyncMock()

    # Fake service for successful invite
    class FakeInviteService:
        def __init__(self, db_, cache_):
            pass

        async def generate_admin_invite(self, data, caller_user_id):
            return {"success": True, "message": "Invite sent", "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'InviteAdminService', FakeInviteService)

    # SUPER_ADMIN can invite ADMIN
    req = SimpleNamespace()
    req.state = SimpleNamespace()
    req.state.user = {"role": "SUPER_ADMIN", "sub": "u1"}

    invite = AdminInviteRequest(email="a@b.com", first_name="A", role="ADMIN")
    resp = await handle_invite_admin_controller(invite, db, cache, req)
    assert resp.status_code == 200

    # HR cannot invite ADMIN -> expect 403
    req2 = SimpleNamespace()
    req2.state = SimpleNamespace()
    req2.state.user = {"role": "HR", "sub": "u2"}

    resp2 = await handle_invite_admin_controller(invite, db, cache, req2)
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_get_all_and_delete_batch_controllers(monkeypatch):
    db = AsyncMock()

    # Fake GetAllAdminsService
    class FakeGetAll:
        def __init__(self, db_):
            pass

        async def get_all_admins(self, caller_role):
            return {"success": True, "data": {"admins": []}, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'GetAllAdminsService', FakeGetAll)

    req = SimpleNamespace()
    req.state = SimpleNamespace()
    req.state.user = {"role": "SUPER_ADMIN"}

    resp = await handle_get_all_admins_controller(db, req)
    assert resp.status_code == 200

    # Fake DeleteAdminsBatchService
    class FakeDeleteBatch:
        def __init__(self, db_):
            pass

        async def delete_admins(self, user_data, caller_role, caller_id):
            return {"success": True, "message": "Deleted", "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'DeleteAdminsBatchService', FakeDeleteBatch)

    delete_req = SimpleNamespace()
    delete_req.user_ids = ["u2"]

    req2 = SimpleNamespace()
    req2.state = SimpleNamespace()
    req2.state.user = {"role": "SUPER_ADMIN", "sub": "u1"}

    resp2 = await handle_delete_admins_batch_controller(delete_req, db, req2)
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_handle_get_admin_by_id_controller(monkeypatch):
    db = AsyncMock()

    class FakeGetById:
        def __init__(self, db_):
            pass

        async def get_admin_details(self, admin_id):
            return {"success": True, "data": {"admin": {"user_id": admin_id}}, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'GetAdminByIdService', FakeGetById)

    resp = await handle_get_admin_by_id_controller("123", db)
    assert resp.status_code == 200
    assert _resp_json(resp)["data"]["admin"]["user_id"] == "123"
import pytest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from fastapi import Response
from fastapi.responses import JSONResponse
import json

from app.controllers.authentication_controller import (
    handle_send_otp_controller,
    handle_resend_otp_controller,
    handle_verify_otp_controller,
    handle_check_email_status_controller,
    handle_check_cookie_controller,
    handle_logout_controller,
    handle_debug_list_emails_controller,
    handle_invite_admin_controller,
    handle_complete_admin_setup_controller,
)


class FakeDB:
    pass


@patch("app.controllers.authentication_controller.SendOtpService")
@pytest.mark.asyncio
async def test_handle_send_otp_returns_success(MockSendSvc):
    mock_service = MockSendSvc.return_value
    mock_service.send_otp = AsyncMock(return_value={"message": "OTP sent", "expires_in": 300})

    user_data = SimpleNamespace(phone="+911234567890")
    res: JSONResponse = await handle_send_otp_controller(user_data, FakeDB(), None)

    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert body["data"]["expires_in"] == 300


@patch("app.controllers.authentication_controller.SendOtpService")
@pytest.mark.asyncio
async def test_handle_send_otp_http_exception(MockSendSvc):
    from fastapi import HTTPException
    mock_service = MockSendSvc.return_value
    mock_service.send_otp = AsyncMock(side_effect=HTTPException(status_code=401, detail='unauth'))

    user_data = SimpleNamespace(phone="+911234567890")
    res: JSONResponse = await handle_send_otp_controller(user_data, FakeDB(), None)
    assert res.status_code == 401
    body = json.loads(res.body)
    assert body["success"] is False


@patch("app.controllers.authentication_controller.ResendOtpService")
@pytest.mark.asyncio
async def test_handle_resend_otp_general_exception(MockResendSvc):
    mock = MockResendSvc.return_value
    mock.resend_otp = AsyncMock(side_effect=Exception("fail"))
    user_data = SimpleNamespace(phone="+911234567890")
    res: JSONResponse = await handle_resend_otp_controller(user_data, FakeDB(), None)
    assert res.status_code == 500
    body = json.loads(res.body)
    assert body["success"] is False


@patch("app.controllers.authentication_controller.VerifyOtpService")
@pytest.mark.asyncio
async def test_handle_verify_otp_http_exception(MockVerifySvc):
    from fastapi import HTTPException
    mock = MockVerifySvc.return_value
    mock.verify_otp = AsyncMock(side_effect=HTTPException(status_code=400, detail='bad'))
    user_data = SimpleNamespace(phone="+911234567890", otp="0000")
    res = await handle_verify_otp_controller(user_data, Response(), FakeDB(), None)
    assert res.status_code == 400



@patch("app.controllers.authentication_controller.ResendOtpService")
@pytest.mark.asyncio
async def test_handle_resend_otp_returns_success(MockResendSvc):
    mock_service = MockResendSvc.return_value
    mock_service.resend_otp = AsyncMock(return_value={"message": "OTP resent", "expires_in": 120})

    user_data = SimpleNamespace(phone="+911234567890")
    res: JSONResponse = await handle_resend_otp_controller(user_data, FakeDB(), None)

    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert body["data"]["expires_in"] == 120


@patch("app.controllers.authentication_controller.VerifyOtpService")
@pytest.mark.asyncio
async def test_handle_verify_otp_returns_service_response(MockVerifySvc):
    mock_service = MockVerifySvc.return_value
    # Controller expects service.verify_otp to return a JSONResponse directly
    mock_service.verify_otp = AsyncMock(return_value=JSONResponse(content={"ok": True}, status_code=201))

    user_data = SimpleNamespace(phone="+911234567890", otp="1234")
    response = Response()
    res = await handle_verify_otp_controller(user_data, response, FakeDB(), None)

    assert isinstance(res, JSONResponse)
    assert res.status_code == 201
    assert json.loads(res.body) == {"ok": True}


@patch("app.controllers.authentication_controller.CheckUserExistenceService")
@pytest.mark.asyncio
async def test_handle_check_email_status_calls_service(MockCheckSvc):
    mock_service = MockCheckSvc.return_value
    mock_service.check_email_status = AsyncMock(return_value={"exists": True, "status_code": 200})

    res = await handle_check_email_status_controller("alice@example.com", FakeDB())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    assert json.loads(res.body)["exists"] is True


@patch("app.controllers.authentication_controller.get_user_by_id", new_callable=AsyncMock)
@patch("app.controllers.authentication_controller.jwt")
@pytest.mark.asyncio
async def test_handle_check_cookie_with_token_and_db(MockJwt, mock_get_user):
    # Simulate cookies with no fn/ln so the controller queries DB
    payload = {"sub": "user-1", "role": "HR", "fn": None, "ln": None}
    MockDecode = AsyncMock()
    MockJwt.decode = lambda token, key, algorithms: payload

    # DB returns user with names
    user = SimpleNamespace(first_name="Alice", last_name="Smith")
    mock_get_user.return_value = user

    request = SimpleNamespace(cookies={"access_token": "tok"})
    res = await handle_check_cookie_controller(request, FakeDB())

    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert body["data"]["first_name"] == "Alice"
    assert body["data"]["role"] == "HR"


@patch("app.controllers.authentication_controller.jwt")
@pytest.mark.asyncio
async def test_handle_check_cookie_expired_returns_401(MockJwt):
    # Make jwt.decode raise ExpiredSignatureError
    from jose import ExpiredSignatureError

    def raise_exp(*args, **kwargs):
        raise ExpiredSignatureError("expired")

    MockJwt.decode = raise_exp

    request = SimpleNamespace(cookies={"access_token": "tok"})
    res = await handle_check_cookie_controller(request, FakeDB())

    assert isinstance(res, JSONResponse)
    assert res.status_code == 401
    body = json.loads(res.body)
    assert body["success"] is False


@patch("app.controllers.authentication_controller.ResendOtpService")
@pytest.mark.asyncio
async def test_handle_resend_otp_constructor_type_error_fallback(MockResendSvc):
    # Make constructor behavior raise TypeError when called with two args and succeed for single arg
    class FakeResend:
        def __init__(self, *args):
            if len(args) == 2:
                raise TypeError("bad constructor")
        async def resend_otp(self, user_data):
            return {"message": "OTP resent from fallback", "expires_in": 90}

    MockResendSvc.side_effect = lambda *args, **kwargs: FakeResend(*args, **kwargs)

    user_data = SimpleNamespace(phone="+911234567890")
    res: JSONResponse = await handle_resend_otp_controller(user_data, FakeDB(), None)
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert body["data"]["expires_in"] == 90


@pytest.mark.asyncio
async def test_handle_debug_list_emails_controller_success():
    class FakeDB:
        async def execute(self, q, *a, **kw):
            class Res:
                def fetchall(self):
                    return [("a@example.com", "HR", "uuid-1"), ("b@example.com", "ADMIN", "uuid-2")]
            return Res()
    res = await handle_debug_list_emails_controller(FakeDB())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert "users" in body["data"]


@pytest.mark.asyncio
async def test_handle_debug_list_emails_controller_error():
    class FakeDB:
        async def execute(self, q, *a, **kw):
            raise Exception("boom")
    res = await handle_debug_list_emails_controller(FakeDB())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 500


@patch("app.controllers.authentication_controller.InviteAdminService")
@pytest.mark.asyncio
async def test_handle_invite_admin_controller_role_checks(MockInviteSvc):
    # Request missing user leads to 401
    user_data = SimpleNamespace(role="ADMIN", email="x@example.com")
    request = SimpleNamespace(state=SimpleNamespace(user=None))
    res = await handle_invite_admin_controller(user_data, FakeDB(), None, request)
    assert res.status_code == 401

    # HR cannot invite ADMIN -> 403
    request2 = SimpleNamespace(state=SimpleNamespace(user={"role": "HR", "user_id": "caller-1"}))
    res2 = await handle_invite_admin_controller(user_data, FakeDB(), None, request2)
    assert res2.status_code == 403

    # ADMIN can invite HR -> success
    user_data_hr = SimpleNamespace(role="HR", email="hr@example.com")
    request3 = SimpleNamespace(state=SimpleNamespace(user={"role": "ADMIN", "user_id": "caller-1"}))
    mock_service = MockInviteSvc.return_value
    mock_service.generate_admin_invite = AsyncMock(return_value={"status_code": 200, "message": "ok"})
    res3 = await handle_invite_admin_controller(user_data_hr, FakeDB(), None, request3)
    assert res3.status_code == 200


@patch("app.controllers.authentication_controller.CompleteAdminSetupService")
@pytest.mark.asyncio
async def test_handle_complete_admin_setup_controller_success(MockCompleteSvc):
    mock = MockCompleteSvc.return_value
    mock.complete_admin_setup = AsyncMock(return_value={"status_code": 201, "message": "created"})
    res = await handle_complete_admin_setup_controller("token123", FakeDB(), None, Response())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 201


@patch("app.controllers.authentication_controller.jwt")
@patch("app.controllers.authentication_controller.add_jti_to_blocklist", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_handle_logout_revokes_tokens_and_deletes_cookies(MockAddJti, MockJwt):
    # Make jwt.decode return jti and exp in the future
    import time
    future = int(time.time()) + 3600
    MockJwt.decode = lambda token, key, algorithms: {"jti": "j1", "exp": future}

    request = SimpleNamespace(cookies={"access_token": "a", "refresh_token": "r"})
    response = Response()

    res = await handle_logout_controller(response, request, None)

    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["success"] is True
