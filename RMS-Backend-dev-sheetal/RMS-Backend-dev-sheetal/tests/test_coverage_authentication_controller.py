import pytest
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Response, Request, HTTPException

from app.controllers.authentication_controller import (
    handle_send_otp_controller,
    handle_resend_otp_controller,
    handle_verify_otp_controller,
    handle_check_email_status_controller,
    handle_invite_admin_controller,
)


@pytest.mark.asyncio
async def test_handle_send_otp_success():
    class FakeService:
        def __init__(self, db, cache):
            pass

        async def send_otp(self, user_data):
            return {"message": "OTP sent", "expires_in": 60}

    with patch('app.controllers.authentication_controller.SendOtpService', FakeService):
        res = await handle_send_otp_controller(SimpleNamespace(email='a@b.com'), AsyncMock(), AsyncMock())
        assert res.status_code == 200
        body = json.loads(res.body)
        assert body.get('data', {}).get('expires_in') == 60


@pytest.mark.asyncio
async def test_handle_send_otp_http_exception():
    class FakeService:
        def __init__(self, db, cache):
            pass

        async def send_otp(self, _):
            raise HTTPException(status_code=400, detail='Bad')

    with patch('app.controllers.authentication_controller.SendOtpService', FakeService):
        res = await handle_send_otp_controller(SimpleNamespace(email='x'), AsyncMock(), AsyncMock())
        assert res.status_code == 400
        body = json.loads(res.body)
        assert body.get('status_code') == 400
        assert body.get('message') == 'Bad'


@pytest.mark.asyncio
async def test_handle_resend_otp_fallback_instantiate():
    # Make a service that only accepts (cache,) so controller falls back
    class FakeResend:
        def __init__(self, cache):
            pass

        async def resend_otp(self, data):
            return {"message": "resent", "expires_in": 30}

    with patch('app.controllers.authentication_controller.ResendOtpService', FakeResend):
        res = await handle_resend_otp_controller(SimpleNamespace(email='a@b.com'), AsyncMock(), AsyncMock())
        assert res.status_code == 200
        body = json.loads(res.body)
        assert body.get('data', {}).get('expires_in') == 30


@pytest.mark.asyncio
async def test_handle_verify_otp_returns_service_response():
    class FakeVerify:
        def __init__(self, db, cache):
            pass

        async def verify_otp(self, data, response: Response):
            return Response(content=json.dumps({"ok": True}), media_type="application/json", status_code=201)

    with patch('app.controllers.authentication_controller.VerifyOtpService', FakeVerify):
        res = await handle_verify_otp_controller(SimpleNamespace(code='1234'), Response(), AsyncMock(), AsyncMock())
        assert getattr(res, 'status_code', None) == 201


@pytest.mark.asyncio
async def test_handle_check_email_status_controller_forwards_service_result():
    class FakeCheck:
        def __init__(self, db):
            pass

        async def check_email_status(self, email):
            return {"status_code": 200, "exists": True}

    with patch('app.controllers.authentication_controller.CheckUserExistenceService', FakeCheck):
        res = await handle_check_email_status_controller('a@b.com', AsyncMock())
        assert res.status_code == 200
        body = json.loads(res.body)
        assert body.get('exists') is True


@pytest.mark.asyncio
async def test_handle_invite_admin_permission_checks():
    # Missing auth
    user_data = SimpleNamespace(role='HR')
    req = MagicMock()
    req.state = SimpleNamespace()
    res = await handle_invite_admin_controller(user_data, AsyncMock(), AsyncMock(), req)
    assert res.status_code == 401

    # HR trying to invite ADMIN -> forbidden
    req2 = MagicMock()
    req2.state.user = {"role": "HR", "sub": "u1"}
    res2 = await handle_invite_admin_controller(SimpleNamespace(role='ADMIN'), AsyncMock(), AsyncMock(), req2)
    assert res2.status_code == 403

    # SUPER_ADMIN can invite
    class FakeInviteService:
        def __init__(self, db, cache):
            pass

        async def generate_admin_invite(self, user_data, caller_user_id):
            return {"status_code": 200, "success": True}

    req3 = MagicMock()
    req3.state.user = {"role": "SUPER_ADMIN", "sub": "u1"}
    with patch('app.controllers.authentication_controller.InviteAdminService', FakeInviteService):
        res3 = await handle_invite_admin_controller(SimpleNamespace(role='ADMIN'), AsyncMock(), AsyncMock(), req3)
        assert res3.status_code == 200
