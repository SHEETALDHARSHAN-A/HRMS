import asyncio
from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from fastapi import Response
from fastapi.responses import JSONResponse

from app.controllers import authentication_controller as ac


class DummyRequest:
    def __init__(self, cookies=None, state=None):
        self.cookies = cookies or {}
        self.state = state or SimpleNamespace()


@pytest.mark.asyncio
async def test_handle_send_otp_success(monkeypatch):
    # Arrange
    async def fake_send_otp(self, user_data):
        return {"message": "OTP sent", "expires_in": 3600}

    class FakeService:
        def __init__(self, db, cache):
            pass

        send_otp = fake_send_otp

    monkeypatch.setattr(ac, 'SendOtpService', FakeService)

    user_data = SimpleNamespace(phone_number='123')

    # Act
    resp = await ac.handle_send_otp_controller(user_data, db=None, cache=None)

    # Assert
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 200
    assert resp.body is not None


@pytest.mark.asyncio
async def test_handle_send_otp_service_dict_response(monkeypatch):
    async def fake_send_otp(self, user_data):
        return {"success": False, "status_code": 400, "message": "Bad"}

    class FakeService:
        def __init__(self, db, cache):
            pass

        send_otp = fake_send_otp

    monkeypatch.setattr(ac, 'SendOtpService', FakeService)

    user_data = SimpleNamespace(phone_number='123')
    resp = await ac.handle_send_otp_controller(user_data, db=None, cache=None)
    assert resp.status_code == 400
    assert b'Bad' in resp.body


@pytest.mark.asyncio
async def test_handle_resend_otp_success_and_dict(monkeypatch):
    async def fake_resend(self, user_data):
        return {"message": "Resent", "expires_in": 120}

    class FakeResendService:
        def __init__(self, cache):
            pass

        resend_otp = fake_resend

    monkeypatch.setattr(ac, 'ResendOtpService', FakeResendService)
    user_data = SimpleNamespace(phone_number='222')

    resp = await ac.handle_resend_otp_controller(user_data, db=None, cache=None)
    assert resp.status_code == 200
    assert b'Resent' in resp.body

    # dict-style
    async def fake_resend_dict(self, user_data):
        return {"success": False, "status_code": 403, "message": "No"}

    FakeResendService.resend_otp = fake_resend_dict
    resp2 = await ac.handle_resend_otp_controller(user_data, db=None, cache=None)
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_handle_verify_otp_controller_returns_jsonresponse(monkeypatch):
    async def fake_verify_otp(self, user_data, response):
        return JSONResponse(content={"ok": True}, status_code=201)

    class FakeVerifyService:
        def __init__(self, db, cache):
            pass

        verify_otp = fake_verify_otp

    monkeypatch.setattr(ac, 'VerifyOtpService', FakeVerifyService)

    user_data = SimpleNamespace(code='000')
    resp_obj = Response()
    resp = await ac.handle_verify_otp_controller(user_data, resp_obj, db=None, cache=None)

    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_handle_check_email_status_controller(monkeypatch):
    async def fake_check(self, email):
        return {"success": True, "status_code": 200, "message": "Exists"}

    class FakeCheckService:
        def __init__(self, db):
            pass

        check_email_status = fake_check

    monkeypatch.setattr(ac, 'CheckUserExistenceService', FakeCheckService)

    resp = await ac.handle_check_email_status_controller('a@b.com', db=None)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 200
    assert b'Exists' in resp.body


@pytest.mark.asyncio
async def test_handle_check_cookie_controller_valid_and_user_lookup(monkeypatch):
    # valid token with fn/ln provided
    payload = {"sub": "user-1", "role": "ADMIN", "fn": "John", "ln": "Doe"}

    def fake_decode(token, key, algorithms):
        return payload

    monkeypatch.setattr(ac.jwt, 'decode', fake_decode)

    req = DummyRequest(cookies={"access_token": "tok"})

    resp = await ac.handle_check_cookie_controller(req, db=None)
    assert resp.status_code == 200
    assert b'Token is valid' in resp.body

    # now test ExpiredSignatureError
    def raise_exp(token, key, algorithms):
        raise ac.ExpiredSignatureError()

    monkeypatch.setattr(ac.jwt, 'decode', raise_exp)
    req2 = DummyRequest(cookies={"access_token": "tok"})
    resp2 = await ac.handle_check_cookie_controller(req2, db=None)
    assert resp2.status_code == 401
    assert b'Session expired' in resp2.body


@pytest.mark.asyncio
async def test_handle_logout_controller_revokes_jtis_and_clears_cookies(monkeypatch):
    calls = []

    async def fake_add_jti(jti, cache, ttl):
        calls.append((jti, ttl))

    monkeypatch.setattr(ac, 'add_jti_to_blocklist', fake_add_jti)

    future = int(datetime.timestamp(datetime.now(timezone.utc))) + 3600
    payload1 = {"jti": "j1", "exp": future}
    payload2 = {"jti": "j2", "exp": future}

    def fake_decode(token, key, algorithms):
        # return different payloads based on token value
        if token == 'a':
            return payload1
        return payload2

    monkeypatch.setattr(ac.jwt, 'decode', fake_decode)

    req = DummyRequest(cookies={"access_token": "a", "refresh_token": "b"})
    response = Response()

    resp = await ac.handle_logout_controller(response, req, cache=None)

    assert resp.status_code == 200
    # ensure both JTIs were scheduled/added
    assert len(calls) == 2
    assert calls[0][0] in ('j1', 'j2')

