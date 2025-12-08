import pytest
from fastapi import HTTPException, Response
import json
from types import SimpleNamespace

import app.controllers.authentication_controller as auth_ctrl
from app.schemas.authentication_request import SendOTPRequest, VerifyOTPRequest, AdminInviteRequest, DeleteAdminsBatchRequest, AdminUpdateRequest


@pytest.mark.asyncio
async def test_handle_send_otp_service_raises_returns_500(monkeypatch):
    async def raise_send_otp(self, user_data):
        raise Exception("send-otp-failure")

    class FakeSendService:
        def __init__(self, db, cache):
            pass

        async def send_otp(self, user_data):
            return await raise_send_otp(self, user_data)

    monkeypatch.setattr(auth_ctrl, "SendOtpService", FakeSendService)

    resp = await auth_ctrl.handle_send_otp_controller(SendOTPRequest(email="x@y.com"), db=None, cache=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "send-otp-failure" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_resend_otp_handles_typeerror_fallback_and_exception(monkeypatch):
    # Provide a ResendOtpService that only accepts (cache,) so first ctor raises TypeError
    class FakeResendServiceSingleArg:
        def __init__(self, cache):
            pass

        async def resend_otp(self, user_data):
            raise Exception("resend-failure")

    monkeypatch.setattr(auth_ctrl, "ResendOtpService", FakeResendServiceSingleArg)

    resp = await auth_ctrl.handle_resend_otp_controller(SendOTPRequest(email="a@b.com"), db=None, cache=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "resend-failure" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_verify_otp_http_exception_returns_status(monkeypatch):
    class FakeVerifyService:
        def __init__(self, db, cache):
            pass

        async def verify_otp(self, user_data, response: Response):
            raise HTTPException(status_code=400, detail="bad otp")

    monkeypatch.setattr(auth_ctrl, "VerifyOtpService", FakeVerifyService)

    resp_obj = Response()
    resp = await auth_ctrl.handle_verify_otp_controller(VerifyOTPRequest(email="u@v.com", otp="1234"), resp_obj, db=None, cache=None)
    assert resp.status_code == 400
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert body.get("status_code") == 400


@pytest.mark.asyncio
async def test_handle_debug_list_emails_db_exception_returns_500():
    class BadDB:
        async def execute(self, *a, **k):
            raise Exception("db-fail")

    resp = await auth_ctrl.handle_debug_list_emails_controller(db=BadDB())
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "db-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_check_email_status_service_exception_returns_500(monkeypatch):
    class FakeCheckService:
        def __init__(self, db):
            pass

        async def check_email_status(self, email):
            raise Exception("check-email-fail")

    monkeypatch.setattr(auth_ctrl, "CheckUserExistenceService", FakeCheckService)

    resp = await auth_ctrl.handle_check_email_status_controller("a@b.com", db=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "check-email-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_verify_otp_generic_exception_returns_500(monkeypatch):
    class FakeVerifyServiceErr:
        def __init__(self, db, cache):
            pass

        async def verify_otp(self, user_data, response: Response):
            raise Exception("verify-fail")

    monkeypatch.setattr(auth_ctrl, "VerifyOtpService", FakeVerifyServiceErr)

    resp_obj = Response()
    resp = await auth_ctrl.handle_verify_otp_controller(VerifyOTPRequest(email="u@v.com", otp="1234"), resp_obj, db=None, cache=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "verify-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_invite_admin_insufficient_permissions():
    # user role not allowed to invite
    user_payload = {"role": "USER", "user_id": "u1"}
    req = SimpleNamespace(state=SimpleNamespace(user=user_payload))

    invite = AdminInviteRequest(email="a@b.com", first_name="A", role="HR")
    resp = await auth_ctrl.handle_invite_admin_controller(invite, db=None, cache=None, request=req)
    assert resp.status_code == 403
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "Insufficient permissions" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_invite_admin_service_http_exception_and_generic(monkeypatch):
    # HTTPException from service should be propagated as controller response
    class FakeInviteServiceHttp:
        def __init__(self, db, cache):
            pass

        async def generate_admin_invite(self, user_data, caller_user_id):
            raise HTTPException(status_code=422, detail="bad invite")

    monkeypatch.setattr(auth_ctrl, "InviteAdminService", FakeInviteServiceHttp)
    user_payload = {"role": "SUPER_ADMIN", "user_id": "u1"}
    req = SimpleNamespace(state=SimpleNamespace(user=user_payload))
    invite = AdminInviteRequest(email="b@c.com", first_name="B", role="ADMIN")
    resp = await auth_ctrl.handle_invite_admin_controller(invite, db=None, cache=None, request=req)
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert body.get("success") is False

    # generic exception case
    class FakeInviteServiceErr:
        def __init__(self, db, cache):
            pass

        async def generate_admin_invite(self, user_data, caller_user_id):
            raise Exception("invite-fail")

    monkeypatch.setattr(auth_ctrl, "InviteAdminService", FakeInviteServiceErr)
    resp2 = await auth_ctrl.handle_invite_admin_controller(invite, db=None, cache=None, request=req)
    assert resp2.status_code == 500
    body2 = json.loads(resp2.body)
    assert body2.get("success") is False
    assert "invite-fail" in (body2.get("message") or "")


@pytest.mark.asyncio
async def test_complete_admin_setup_service_exceptions(monkeypatch):
    class FakeCompleteHttp:
        def __init__(self, db, cache):
            pass

        async def complete_admin_setup(self, token, response):
            raise HTTPException(status_code=400, detail="bad token")

    monkeypatch.setattr(auth_ctrl, "CompleteAdminSetupService", FakeCompleteHttp)
    resp = await auth_ctrl.handle_complete_admin_setup_controller("t", db=None, cache=None, response=Response())
    assert resp.status_code == 400

    class FakeCompleteErr:
        def __init__(self, db, cache):
            pass

        async def complete_admin_setup(self, token, response):
            raise Exception("complete-fail")

    monkeypatch.setattr(auth_ctrl, "CompleteAdminSetupService", FakeCompleteErr)
    resp2 = await auth_ctrl.handle_complete_admin_setup_controller("t2", db=None, cache=None, response=Response())
    assert resp2.status_code == 500
    body = json.loads(resp2.body)
    assert body.get("success") is False
    assert "complete-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_get_all_admins_missing_user_and_service_exception(monkeypatch):
    # missing user -> 401
    req_none = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await auth_ctrl.handle_get_all_admins_controller(db=None, request=req_none)
    assert resp.status_code == 401

    # service raises -> 500
    class FakeGetAll:
        def __init__(self, db):
            pass

        async def get_all_admins(self, caller_role=None):
            raise Exception("getall-fail")

    monkeypatch.setattr(auth_ctrl, "GetAllAdminsService", FakeGetAll)
    req = SimpleNamespace(state=SimpleNamespace(user={"role": "SUPER_ADMIN"}))
    resp2 = await auth_ctrl.handle_get_all_admins_controller(db=None, request=req)
    assert resp2.status_code == 500
    body = json.loads(resp2.body)
    assert body.get("success") is False
    assert "getall-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_delete_admins_batch_missing_user_and_service_errors(monkeypatch):
    data = DeleteAdminsBatchRequest(user_ids=["u1"])
    req_none = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await auth_ctrl.handle_delete_admins_batch_controller(data, db=None, request=req_none)
    assert resp.status_code == 401

    class FakeDeleteHttp:
        def __init__(self, db):
            pass

        async def delete_admins(self, user_data, caller_role=None, caller_id=None):
            raise HTTPException(status_code=422, detail="bad batch")

    monkeypatch.setattr(auth_ctrl, "DeleteAdminsBatchService", FakeDeleteHttp)
    req = SimpleNamespace(state=SimpleNamespace(user={"role": "SUPER_ADMIN", "sub": "u1"}))
    resp2 = await auth_ctrl.handle_delete_admins_batch_controller(data, db=None, request=req)
    assert resp2.status_code == 422

    class FakeDeleteErr:
        def __init__(self, db):
            pass

        async def delete_admins(self, user_data, caller_role=None, caller_id=None):
            raise Exception("delete-fail")

    monkeypatch.setattr(auth_ctrl, "DeleteAdminsBatchService", FakeDeleteErr)
    resp3 = await auth_ctrl.handle_delete_admins_batch_controller(data, db=None, request=req)
    assert resp3.status_code == 500
    body = json.loads(resp3.body)
    assert "delete-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_resend_otp_http_exception_propagates(monkeypatch):
    class FakeResendHttp:
        def __init__(self, cache, db=None):
            pass

        async def resend_otp(self, user_data):
            raise HTTPException(status_code=429, detail="too many")

    monkeypatch.setattr(auth_ctrl, "ResendOtpService", FakeResendHttp)
    resp = await auth_ctrl.handle_resend_otp_controller(SendOTPRequest(email="x@y.com"), db=None, cache=None)
    assert resp.status_code == 429
    body = json.loads(resp.body)
    assert body.get("status_code") == 429


@pytest.mark.asyncio
async def test_handle_check_email_status_http_exception(monkeypatch):
    class FakeCheckHttp:
        def __init__(self, db):
            pass

        async def check_email_status(self, email):
            raise HTTPException(status_code=404, detail="not found")

    monkeypatch.setattr(auth_ctrl, "CheckUserExistenceService", FakeCheckHttp)
    resp = await auth_ctrl.handle_check_email_status_controller("z@z.com", db=None)
    assert resp.status_code == 404
    body = json.loads(resp.body)
    assert body.get("status_code") == 404
@pytest.mark.asyncio
async def test_get_admin_by_id_service_exceptions(monkeypatch):
    class FakeGetHttp:
        def __init__(self, db):
            pass

        async def get_admin_details(self, admin_id):
            raise HTTPException(status_code=404, detail="not found")

    monkeypatch.setattr(auth_ctrl, "GetAdminByIdService", FakeGetHttp)
    resp = await auth_ctrl.handle_get_admin_by_id_controller("a1", db=None)
    assert resp.status_code == 404

    class FakeGetErr:
        def __init__(self, db):
            pass

        async def get_admin_details(self, admin_id):
            raise Exception("get-admin-fail")

    monkeypatch.setattr(auth_ctrl, "GetAdminByIdService", FakeGetErr)
    resp2 = await auth_ctrl.handle_get_admin_by_id_controller("a2", db=None)
    assert resp2.status_code == 500
    body = json.loads(resp2.body)
    assert "get-admin-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_update_admin_missing_user_and_service_exceptions(monkeypatch):
    data = AdminUpdateRequest(first_name="X")
    req_none = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await auth_ctrl.handle_update_admin_controller("aid", data, db=None, cache=None, request=req_none)
    assert resp.status_code == 401

    class FakeUpdateHttp:
        def __init__(self, db, cache):
            pass

        async def update_admin_details(self, admin_id, user_data, caller_role=None, caller_id=None):
            raise HTTPException(status_code=422, detail="bad update")

    monkeypatch.setattr(auth_ctrl, "UpdateAdminService", FakeUpdateHttp)
    req = SimpleNamespace(state=SimpleNamespace(user={"role": "ADMIN", "sub": "u1"}))
    resp2 = await auth_ctrl.handle_update_admin_controller("aid", data, db=None, cache=None, request=req)
    assert resp2.status_code == 422

    class FakeUpdateErr:
        def __init__(self, db, cache):
            pass

        async def update_admin_details(self, admin_id, user_data, caller_role=None, caller_id=None):
            raise Exception("update-fail")

    monkeypatch.setattr(auth_ctrl, "UpdateAdminService", FakeUpdateErr)
    resp3 = await auth_ctrl.handle_update_admin_controller("aid", data, db=None, cache=None, request=req)
    assert resp3.status_code == 500
    body = json.loads(resp3.body)
    assert "update-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_verify_admin_name_update_handles_exceptions(monkeypatch):
    class FakeVerifyErr:
        def __init__(self, db, cache):
            pass

        async def verify_name_update(self, token, user_id):
            raise Exception("name-verify-fail")

    monkeypatch.setattr(auth_ctrl, "UpdateAdminService", FakeVerifyErr)
    resp = await auth_ctrl.handle_verify_admin_name_update_controller("t", "u1", db=None, cache=None)
    # should redirect to processing with status=error
    assert resp.status_code == 302
    assert "status=error" in resp.headers.get("location", "")

@pytest.mark.asyncio
async def test_verify_admin_phone_update_exception_returns_redirect(monkeypatch):
    class FakeUpdateErr:
        def __init__(self, db, cache):
            pass

        async def verify_phone_update(self, token, user_id):
            raise Exception("phone-verify-fail")

    monkeypatch.setattr(auth_ctrl, "UpdateAdminService", FakeUpdateErr)
    resp = await auth_ctrl.handle_verify_admin_phone_update_controller("t", "u1", db=None, cache=None)
    assert resp.status_code == 302
    # Location should indicate phone_update and status=error
    loc = resp.headers.get("location", "")
    assert "type=phone_update" in loc
    assert "status=error" in loc


@pytest.mark.asyncio
async def test_verify_admin_email_update_exception_returns_500(monkeypatch):
    class FakeUpdateErr:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, user_data):
            raise Exception("email-verify-fail")

    monkeypatch.setattr(auth_ctrl, "UpdateAdminService", FakeUpdateErr)
    fake_req = SimpleNamespace(token="t", user_id="u1", new_email="n@e.com")
    resp = await auth_ctrl.handle_verify_admin_email_update_controller(fake_req, db=None, cache=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "email-verify-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_check_cookie_uses_refresh_token_and_decodes(monkeypatch):
    # Provide only refresh_token cookie and have jwt.decode return payload
    def fake_decode(token, secret, algorithms=None):
        return {"sub": "u1", "role": "ADMIN", "fn": "F", "ln": "L"}

    monkeypatch.setattr(auth_ctrl, "jwt", SimpleNamespace(decode=fake_decode))
    req = SimpleNamespace(cookies={"refresh_token": "rt"})
    resp = await auth_ctrl.handle_check_cookie_controller(req, db=None)
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("success") is True
    data = body.get("data") or {}
    assert data.get("first_name") == "F"
    assert data.get("last_name") == "L"


@pytest.mark.asyncio
async def test_handle_check_cookie_decode_exception_returns_500(monkeypatch):
    # Make jwt.decode raise a generic Exception
    def bad_decode(*a, **k):
        raise Exception("decode-fail")

    monkeypatch.setattr(auth_ctrl, "jwt", SimpleNamespace(decode=bad_decode))
    req = SimpleNamespace(cookies={"access_token": "at"})
    resp = await auth_ctrl.handle_check_cookie_controller(req, db=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "Token processing error" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_handle_check_cookie_db_fetch_failure_defaults_user_none(monkeypatch):
    # jwt.decode returns payload without fn/ln so DB fetch is attempted
    def decode_no_names(*a, **k):
        return {"sub": "u2", "role": "USER"}

    async def bad_get_user(db, user_id):
        raise Exception("db-lookup-fail")

    monkeypatch.setattr(auth_ctrl, "jwt", SimpleNamespace(decode=decode_no_names))
    monkeypatch.setattr(auth_ctrl, "get_user_by_id", bad_get_user)
    req = SimpleNamespace(cookies={"access_token": "at"})
    resp = await auth_ctrl.handle_check_cookie_controller(req, db=None)
    assert resp.status_code == 200
    body = json.loads(resp.body)
    data = body.get("data") or {}
    # Since DB fetch failed and no names in token, defaults should be used
    assert data.get("first_name") == "Authenticated"
    assert data.get("last_name") == "User"


@pytest.mark.asyncio
async def test_handle_logout_ignores_jwt_errors(monkeypatch):
    # Make jwt.decode raise JWTError to exercise the except (JWTError, ExpiredSignatureError): pass
    def raise_jwt(*a, **k):
        raise auth_ctrl.JWTError("bad jwt")

    monkeypatch.setattr(auth_ctrl, "jwt", SimpleNamespace(decode=raise_jwt))
    req = SimpleNamespace(cookies={"access_token": "at", "refresh_token": "rt"})
    resp_obj = Response()
    resp = await auth_ctrl.handle_logout_controller(resp_obj, req, cache=None)
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("success") is True


