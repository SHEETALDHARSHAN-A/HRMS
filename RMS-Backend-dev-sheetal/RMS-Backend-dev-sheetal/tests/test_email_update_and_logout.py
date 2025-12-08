import pytest
import types
import time
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse

import app.controllers.authentication_controller as auth_ctrl


class DummyResponse:
    def __init__(self):
        self.deleted = []

    def delete_cookie(self, name, path="/"):
        self.deleted.append((name, path))


class DummyReq:
    def __init__(self, cookies=None):
        self.cookies = cookies or {}
        import types as _types
        self.state = _types.SimpleNamespace()


@pytest.mark.asyncio
async def test_complete_email_update_success_and_errors(monkeypatch):
    # Ensure frontend_url exists
    monkeypatch.setattr(auth_ctrl.settings, 'frontend_url', 'http://testserver', raising=False)

    class FakeServiceSuccess:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, req_data):
            return {"success": True}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceSuccess)
    res = await auth_ctrl.handle_complete_email_update_controller(token='t', user_id='u', new_email='a@b.c', db=None, cache=None)
    assert isinstance(res, RedirectResponse)
    assert 'status=email_updated' in res.headers.get('location')

    # HTTPException path
    class FakeServiceHTTP:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, req_data):
            raise HTTPException(status_code=400, detail='bad')

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceHTTP)
    res2 = await auth_ctrl.handle_complete_email_update_controller(token='t', user_id='u', new_email='a@b.c', db=None, cache=None)
    assert isinstance(res2, RedirectResponse)
    assert 'status=error' in res2.headers.get('location')

    # Generic exception path
    class FakeServiceExc:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, req_data):
            raise Exception('boom')

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceExc)
    res3 = await auth_ctrl.handle_complete_email_update_controller(token='t', user_id='u', new_email='a@b.c', db=None, cache=None)
    assert isinstance(res3, RedirectResponse)
    assert 'status=error' in res3.headers.get('location')

    # Service returns unsuccessful result (no exception) -> JSONResponse server error
    class FakeServiceNoSuccess:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, req_data):
            return {"success": False}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceNoSuccess)
    res4 = await auth_ctrl.handle_complete_email_update_controller(token='t', user_id='u', new_email='a@b.c', db=None, cache=None)
    assert isinstance(res4, JSONResponse)
    assert res4.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_approve_email_update_branches(monkeypatch):
    monkeypatch.setattr(auth_ctrl.settings, 'frontend_url', 'http://testserver', raising=False)

    class FakeServiceOk:
        def __init__(self, db, cache):
            pass

        async def approve_email_update(self, token, user_id):
            return {"success": True, "data": {"new_email": "n@e.com"}}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceOk)
    res = await auth_ctrl.handle_approve_email_update_controller(token='t', user_id='u', db=None, cache=None)
    assert isinstance(res, RedirectResponse)
    assert 'email_transfer_approved' in res.headers.get('location')

    class FakeServiceFail:
        def __init__(self, db, cache):
            pass

        async def approve_email_update(self, token, user_id):
            return {"success": False, "message": "nope"}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceFail)
    res2 = await auth_ctrl.handle_approve_email_update_controller(token='t', user_id='u', db=None, cache=None)
    assert isinstance(res2, RedirectResponse)
    assert 'email_transfer_error' in res2.headers.get('location')

    class FakeServiceExc:
        def __init__(self, db, cache):
            pass

        async def approve_email_update(self, token, user_id):
            raise Exception('boom')

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceExc)
    res3 = await auth_ctrl.handle_approve_email_update_controller(token='t', user_id='u', db=None, cache=None)
    assert isinstance(res3, RedirectResponse)
    assert 'email_transfer_error' in res3.headers.get('location')


@pytest.mark.asyncio
async def test_logout_revokes_tokens_and_deletes_cookies(monkeypatch):
    # Prepare tokens with jti and exp in future
    future = int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())
    payload = {"jti": "j1", "exp": future}

    # Patch jwt.decode used inside controller
    monkeypatch.setattr(auth_ctrl, 'jwt', types.SimpleNamespace(decode=lambda token, secret, algorithms=None: payload))

    # Track calls to add_jti_to_blocklist
    called = []

    async def fake_add_jti(jti, cache, max_age_seconds):
        called.append((jti, max_age_seconds))

    monkeypatch.setattr(auth_ctrl, 'add_jti_to_blocklist', fake_add_jti)

    # Create dummy cache where set is async (not used because we patch add_jti_to_blocklist)
    dummy_cache = object()

    req = DummyReq(cookies={"access_token": "a", "refresh_token": "r"})
    resp = DummyResponse()

    res = await auth_ctrl.handle_logout_controller(response=resp, request=req, cache=dummy_cache)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_200_OK
    # Cookies should be deleted
    assert ('access_token', '/') in resp.deleted
    assert ('refresh_token', '/') in resp.deleted
    # add_jti_to_blocklist should have been called for each token
    assert any(c[0] == 'j1' for c in called)
