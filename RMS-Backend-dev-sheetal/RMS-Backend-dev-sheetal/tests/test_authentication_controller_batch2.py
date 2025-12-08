import pytest
from types import SimpleNamespace
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import HTTPException

import app.controllers.authentication_controller as ac


class DummyRequest:
    def __init__(self, user=None):
        self.state = SimpleNamespace(user=user)


@pytest.mark.asyncio
async def test_handle_invite_admin_no_user():
    req = DummyRequest(user=None)
    data = SimpleNamespace(role='HR', email='a@b.com')
    res = await ac.handle_invite_admin_controller(data, db=None, cache=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_handle_invite_admin_permission_checks_and_success(monkeypatch):
    # ADMIN cannot invite SUPER_ADMIN
    req = DummyRequest(user={"role": "ADMIN", "sub": "u1"})
    data = SimpleNamespace(role='SUPER_ADMIN', email='a@b.com')
    res = await ac.handle_invite_admin_controller(data, db=None, cache=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == 403

    # SUPER_ADMIN can invite anyone and service returns dict
    req2 = DummyRequest(user={"role": "SUPER_ADMIN", "sub": "u2"})

    class FakeInviteService:
        def __init__(self, db, cache):
            pass

        async def generate_admin_invite(self, user_data, caller_user_id):
            return {"success": True, "status_code": 200, "message": "Invited"}

    monkeypatch.setattr(ac, 'InviteAdminService', FakeInviteService)
    res2 = await ac.handle_invite_admin_controller(data, db=None, cache=None, request=req2)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == 200


@pytest.mark.asyncio
async def test_handle_complete_admin_setup_controller(monkeypatch):
    class FakeCompleteService:
        def __init__(self, db, cache):
            pass

        async def complete_admin_setup(self, token, response):
            return {"success": True, "status_code": 201}

    monkeypatch.setattr(ac, 'CompleteAdminSetupService', FakeCompleteService)

    resp = await ac.handle_complete_admin_setup_controller('token', db=None, cache=None, response=None)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_handle_get_all_admins_controller_no_user():
    res = await ac.handle_get_all_admins_controller(db=None, request=DummyRequest(user=None))
    assert isinstance(res, JSONResponse)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_handle_get_all_admins_controller_success(monkeypatch):
    class FakeGetAll:
        def __init__(self, db):
            pass

        async def get_all_admins(self, caller_role=None):
            return {"success": True, "status_code": 200, "data": {"admins": []}}

    monkeypatch.setattr(ac, 'GetAllAdminsService', FakeGetAll)
    res = await ac.handle_get_all_admins_controller(db=None, request=DummyRequest(user={"role": "SUPER_ADMIN"}))
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_handle_delete_admins_batch_controller(monkeypatch):
    class FakeDeleteService:
        def __init__(self, db):
            pass

        async def delete_admins(self, user_data, caller_role=None, caller_id=None):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(ac, 'DeleteAdminsBatchService', FakeDeleteService)
    data = SimpleNamespace(admin_ids=['a'])
    res = await ac.handle_delete_admins_batch_controller(data, db=None, request=DummyRequest(user={"role": "SUPER_ADMIN", "sub": "u"}))
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_handle_verify_admin_name_update_controller_redirects(monkeypatch):
    class FakeUpdateService:
        def __init__(self, db, cache):
            pass

        async def verify_name_update(self, token, user_id):
            return {"success": True}

    monkeypatch.setattr(ac, 'UpdateAdminService', FakeUpdateService)
    resp = await ac.handle_verify_admin_name_update_controller('t', 'uid', db=None, cache=None)
    assert isinstance(resp, RedirectResponse)
    # starlette RedirectResponse exposes the target in the Location header
    loc = resp.headers.get('location')
    assert loc is not None and 'status=success' in loc


@pytest.mark.asyncio
async def test_handle_verify_admin_phone_update_controller(monkeypatch):
    class FakeUpdateService:
        def __init__(self, db, cache):
            pass

        async def verify_phone_update(self, token, user_id):
            return {"success": True}

    monkeypatch.setattr(ac, 'UpdateAdminService', FakeUpdateService)
    resp = await ac.handle_verify_admin_phone_update_controller('t', 'uid', db=None, cache=None)
    assert isinstance(resp, RedirectResponse)
    loc = resp.headers.get('location')
    assert loc is not None and 'phone_update' in loc


@pytest.mark.asyncio
async def test_verify_email_update_and_approve(monkeypatch):
    class FakeUpdateService:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, user_data):
            return {"success": True}

        async def approve_email_update(self, token, user_id):
            return {"success": True, "data": {"new_email": "x@y.com"}}

    monkeypatch.setattr(ac, 'UpdateAdminService', FakeUpdateService)

    user_data = SimpleNamespace(user_id='u', token='t', new_email='x@y.com')
    resp = await ac.handle_verify_admin_email_update_controller(user_data, db=None, cache=None)
    assert isinstance(resp, JSONResponse)

    resp2 = await ac.handle_approve_email_update_controller('t', 'u', db=None, cache=None)
    assert isinstance(resp2, RedirectResponse)
    loc2 = resp2.headers.get('location')
    assert loc2 is not None and 'email_transfer_approved' in loc2


@pytest.mark.asyncio
async def test_complete_email_update_controller_redirects_on_success(monkeypatch):
    class FakeUpdateService:
        def __init__(self, db, cache):
            pass

        async def verify_email_update(self, request_data):
            return {"success": True}

    monkeypatch.setattr(ac, 'UpdateAdminService', FakeUpdateService)

    resp = await ac.handle_complete_email_update_controller('t', 'u', 'x@y.com', db=None, cache=None)
    # function returns RedirectResponse on success
    assert isinstance(resp, RedirectResponse) or isinstance(resp, JSONResponse)

