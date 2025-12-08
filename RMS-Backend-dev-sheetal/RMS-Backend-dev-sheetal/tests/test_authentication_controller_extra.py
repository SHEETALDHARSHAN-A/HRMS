import pytest
import types

import asyncio

from fastapi import status
from fastapi.responses import JSONResponse

import app.controllers.authentication_controller as auth_ctrl


class DummyReq:
    def __init__(self, cookies=None, state_user=None):
        self.cookies = cookies or {}
        self.state = types.SimpleNamespace()
        if state_user is not None:
            self.state.user = state_user


class DummyUser:
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name


@pytest.mark.asyncio
async def test_handle_resend_otp_falls_back_to_single_arg(monkeypatch):
    # Make ResendOtpService only accept a single arg so the two-arg init raises TypeError
    class FakeResend:
        def __init__(self, cache):
            self.cache = cache

        async def resend_otp(self, user_data):
            return {"message": "ok", "expires_in": 60}

    monkeypatch.setattr(auth_ctrl, "ResendOtpService", FakeResend)

    res = await auth_ctrl.handle_resend_otp_controller(user_data=types.SimpleNamespace(), db=None, cache=None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_200_OK
    body = res.body.decode() if hasattr(res, 'body') else None
    # JSONResponse body will be compact; verify success key exists
    assert '"success":true' in body.lower()


@pytest.mark.asyncio
async def test_handle_invite_admin_missing_auth(monkeypatch):
    # No user on request.state should return 401
    monkeypatch.setattr(auth_ctrl, "InviteAdminService", lambda *args, **kwargs: None)
    req = DummyReq(cookies={}, state_user=None)
    user_data = types.SimpleNamespace(role="HR")
    res = await auth_ctrl.handle_invite_admin_controller(user_data, db=None, cache=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_handle_invite_admin_role_restrictions(monkeypatch):
    # ADMIN inviting SUPER_ADMIN should be forbidden
    class FakeInvite:
        def __init__(self, db, cache=None):
            pass

        async def generate_admin_invite(self, user_data, caller_user_id):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, "InviteAdminService", FakeInvite)

    # ADMIN trying to invite SUPER_ADMIN -> forbidden
    req = DummyReq(state_user={"role": "ADMIN", "user_id": "u1"})
    user_data = types.SimpleNamespace(role="SUPER_ADMIN")
    res = await auth_ctrl.handle_invite_admin_controller(user_data, db=None, cache=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # HR trying to invite HR (allowed)
    req2 = DummyReq(state_user={"role": "HR", "user_id": "u2"})
    user_data2 = types.SimpleNamespace(role="HR")
    res2 = await auth_ctrl.handle_invite_admin_controller(user_data2, db=None, cache=None, request=req2)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_handle_check_cookie_token_missing_and_expired(monkeypatch):
    # No tokens -> 401
    req = DummyReq(cookies={})
    res = await auth_ctrl.handle_check_cookie_controller(req, db=None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    # Token expired -> ExpiredSignatureError path
    from jose import ExpiredSignatureError

    def fake_decode_raise(token, secret, algorithms=None):
        raise ExpiredSignatureError("expired")

    monkeypatch.setattr(auth_ctrl, 'jwt', types.SimpleNamespace(decode=fake_decode_raise))
    req2 = DummyReq(cookies={"access_token": "tok"})
    # Ensure settings provide secret/algorithm
    monkeypatch.setattr(auth_ctrl.settings, 'secret_key', 's', raising=False)
    monkeypatch.setattr(auth_ctrl.settings, 'algorithm', 'HS256', raising=False)

    res2 = await auth_ctrl.handle_check_cookie_controller(req2, db=None)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_handle_check_cookie_populates_user_from_db(monkeypatch):
    # When fn/ln missing, controller fetches from DB
    payload = {"sub": "user-1", "role": "ADMIN", "fn": None, "ln": None}

    def fake_decode(token, secret, algorithms=None):
        return payload

    async def fake_get_user_by_id(db, user_id):
        return DummyUser(first_name="Alice", last_name="Smith")

    monkeypatch.setattr(auth_ctrl, 'jwt', types.SimpleNamespace(decode=fake_decode))
    monkeypatch.setattr(auth_ctrl, 'get_user_by_id', fake_get_user_by_id)
    monkeypatch.setattr(auth_ctrl.settings, 'secret_key', 's', raising=False)
    monkeypatch.setattr(auth_ctrl.settings, 'algorithm', 'HS256', raising=False)

    req = DummyReq(cookies={"access_token": "tok"})
    res = await auth_ctrl.handle_check_cookie_controller(req, db=None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_200_OK
    body = res.body.decode()
    assert 'alice' in body.lower()
import time
import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock

from jose import jwt
from fastapi.responses import JSONResponse

from app.controllers import authentication_controller as auth_ctrl
from app.utils.standard_response_utils import ResponseBuilder


@pytest.mark.asyncio
async def test_handle_send_otp_controller_success(monkeypatch):
    # Fake service that returns message/expires_in
    class FakeSend:
        def __init__(self, db, cache):
            pass

        async def send_otp(self, data):
            return {"message": "OTP sent", "expires_in": 300}

    monkeypatch.setattr(auth_ctrl, "SendOtpService", FakeSend)

    res = await auth_ctrl.handle_send_otp_controller(type("Req", (), {"email": "x@x.com"})(), db=MagicMock(), cache=MagicMock())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    body = res.body.decode()
    assert "OTP sent" in body


@pytest.mark.asyncio
async def test_handle_resend_otp_controller_success(monkeypatch):
    class FakeResend:
        def __init__(self, cache):
            pass

        async def resend_otp(self, data):
            return {"message": "OTP resent", "expires_in": 120}

    monkeypatch.setattr(auth_ctrl, "ResendOtpService", FakeResend)

    res = await auth_ctrl.handle_resend_otp_controller(type("Req", (), {"email": "y@y.com"})(), db=MagicMock(), cache=MagicMock())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    assert "OTP resent" in res.body.decode()


@pytest.mark.asyncio
async def test_handle_verify_otp_controller_returns_response(monkeypatch):
    # Verify service returns JSONResponse directly
    class FakeVerify:
        def __init__(self, db, cache):
            pass

        async def verify_otp(self, data, response):
            return JSONResponse(content=ResponseBuilder.success("ok", {"token": "t"}), status_code=200)

    monkeypatch.setattr(auth_ctrl, "VerifyOtpService", FakeVerify)

    res = await auth_ctrl.handle_verify_otp_controller(type("Req", (), {"email": "z@z.com", "otp": "1234"})(), response=MagicMock(), db=MagicMock(), cache=MagicMock())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    assert b'"token":"t"' in res.body


@pytest.mark.asyncio
async def test_handle_check_email_status_controller(monkeypatch):
    class FakeCheck:
        def __init__(self, db):
            pass

        async def check_email_status(self, email):
            return {"success": True, "status_code": 200, "message": "exists", "data": {"exists": False}}

    monkeypatch.setattr(auth_ctrl, "CheckUserExistenceService", FakeCheck)

    res = await auth_ctrl.handle_check_email_status_controller("abc@example.com", db=MagicMock())
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200
    assert b"exists" in res.body


@pytest.mark.asyncio
async def test_handle_check_cookie_valid_and_expired(monkeypatch):
    # Set test secret and algorithm
    monkeypatch.setattr(auth_ctrl.settings, "secret_key", "testsecret")
    monkeypatch.setattr(auth_ctrl.settings, "algorithm", "HS256")

    # valid token
    payload = {"sub": "user-1", "role": "ADMIN", "fn": "First", "ln": "Last", "exp": int(time.time()) + 60}
    token = jwt.encode(payload, auth_ctrl.settings.secret_key, algorithm=auth_ctrl.settings.algorithm)

    request = MagicMock()
    request.cookies = {"access_token": token}

    res = await auth_ctrl.handle_check_cookie_controller(request=request, db=MagicMock())
    assert res.status_code == 200
    assert b"Token is valid" in res.body

    # expired token
    payload2 = {"sub": "user-2", "role": "ADMIN", "fn": "F", "ln": "L", "exp": int(time.time()) - 10}
    token2 = jwt.encode(payload2, auth_ctrl.settings.secret_key, algorithm=auth_ctrl.settings.algorithm)
    request2 = MagicMock()
    request2.cookies = {"access_token": token2}

    res2 = await auth_ctrl.handle_check_cookie_controller(request=request2, db=MagicMock())
    assert res2.status_code == 401
    assert b"Session expired" in res2.body


@pytest.mark.asyncio
async def test_handle_logout_controller_revokes_and_deletes(monkeypatch):
    # Prepare tokens with future exp and jti
    monkeypatch.setattr(auth_ctrl.settings, "secret_key", "testsecret")
    monkeypatch.setattr(auth_ctrl.settings, "algorithm", "HS256")

    exp = int(time.time()) + 300
    payload = {"jti": "jti-1", "exp": exp}
    token = jwt.encode(payload, auth_ctrl.settings.secret_key, algorithm=auth_ctrl.settings.algorithm)

    request = MagicMock()
    request.cookies = {"access_token": token, "refresh_token": token}

    # patch add_jti_to_blocklist to be awaitable
    monkeypatch.setattr(auth_ctrl, "add_jti_to_blocklist", AsyncMock(return_value=None))

    cache = AsyncMock()
    response = MagicMock()

    res = await auth_ctrl.handle_logout_controller(response=response, request=request, cache=cache)
    assert res.status_code == 200
    # ensure cookies were deleted via delete_cookie on response
    assert response.delete_cookie.called
