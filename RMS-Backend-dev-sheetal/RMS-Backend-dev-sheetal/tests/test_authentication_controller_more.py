import pytest
import types

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse

import app.controllers.authentication_controller as auth_ctrl


class Req:
    def __init__(self, user=None, cookies=None):
        import types as _types
        self.state = _types.SimpleNamespace()
        if user is not None:
            self.state.user = user
        else:
            # leave state.user unset for missing auth cases
            pass
        self.cookies = cookies or {}


@pytest.mark.asyncio
async def test_complete_admin_setup_success(monkeypatch):
    class FakeService:
        def __init__(self, db, cache):
            pass

        async def complete_admin_setup(self, token, response):
            return {"success": True, "status_code": 201}

    monkeypatch.setattr(auth_ctrl, 'CompleteAdminSetupService', FakeService)

    res = await auth_ctrl.handle_complete_admin_setup_controller('tkn', db=None, cache=None, response=None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_get_all_admins_missing_auth_and_success(monkeypatch):
    # Missing auth
    req = Req(user=None)
    res = await auth_ctrl.handle_get_all_admins_controller(db=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    # Success path
    class FakeService:
        def __init__(self, db):
            pass

        async def get_all_admins(self, caller_role=None):
            return {"success": True, "status_code": 200, "data": {"admins": []}}

    monkeypatch.setattr(auth_ctrl, 'GetAllAdminsService', FakeService)
    req2 = Req(user={"role": "SUPER_ADMIN"})
    res2 = await auth_ctrl.handle_get_all_admins_controller(db=None, request=req2)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_delete_admins_batch_missing_auth_and_success(monkeypatch):
    req = Req(user=None)
    res = await auth_ctrl.handle_delete_admins_batch_controller(user_data=types.SimpleNamespace(), db=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    class FakeService:
        def __init__(self, db):
            pass

        async def delete_admins(self, user_data, caller_role=None, caller_id=None):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'DeleteAdminsBatchService', FakeService)
    req2 = Req(user={"role": "SUPER_ADMIN", "sub": "u1"})
    res2 = await auth_ctrl.handle_delete_admins_batch_controller(user_data=types.SimpleNamespace(), db=None, request=req2)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_admin_by_id_success_and_http_exception(monkeypatch):
    class FakeService:
        def __init__(self, db):
            pass

        async def get_admin_details(self, admin_id):
            return {"success": True, "status_code": 200, "data": {"admin": {"id": admin_id}}}

    monkeypatch.setattr(auth_ctrl, 'GetAdminByIdService', FakeService)
    res = await auth_ctrl.handle_get_admin_by_id_controller('abc', db=None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_200_OK

    class RaiseService:
        def __init__(self, db):
            pass

        async def get_admin_details(self, admin_id):
            raise HTTPException(status_code=404, detail="Not found")

    monkeypatch.setattr(auth_ctrl, 'GetAdminByIdService', RaiseService)
    res2 = await auth_ctrl.handle_get_admin_by_id_controller('abc', db=None)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_search_admins_success_and_exception(monkeypatch):
    # Patch repository search_admins
    async def fake_search(db, query):
        return [{"id": "1"}]

    monkeypatch.setattr('app.controllers.authentication_controller.search_admins', fake_search, raising=False)
    # Alternatively patch the import path used in function
    import app.db.repository.user_repository as ur
    monkeypatch.setattr(ur, 'search_admins', fake_search)

    res = await auth_ctrl.handle_search_admins_controller('q', db=None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_200_OK

    async def fake_search_raise(db, query):
        raise Exception("boom")

    monkeypatch.setattr(ur, 'search_admins', fake_search_raise)
    res2 = await auth_ctrl.handle_search_admins_controller('q', db=None)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_update_admin_missing_auth_and_success(monkeypatch):
    req = Req(user=None)
    res = await auth_ctrl.handle_update_admin_controller('id', user_data=types.SimpleNamespace(), db=None, cache=None, request=req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    class FakeService:
        def __init__(self, db, cache):
            pass

        async def update_admin_details(self, admin_id, user_data, caller_role=None, caller_id=None):
            return {"success": True, "status_code": 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    req2 = Req(user={"role": "SUPER_ADMIN", "sub": "u1"})
    res2 = await auth_ctrl.handle_update_admin_controller('id', user_data=types.SimpleNamespace(), db=None, cache=None, request=req2)
    assert isinstance(res2, JSONResponse)
    assert res2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_verify_admin_name_update_redirect_branches(monkeypatch):
    class FakeService:
        def __init__(self, db, cache):
            pass

        async def verify_name_update(self, token, user_id):
            return {"success": True}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    res = await auth_ctrl.handle_verify_admin_name_update_controller(token='t', user_id='u', db=None, cache=None)
    assert isinstance(res, RedirectResponse)
    assert 'status=success' in res.headers.get('location')

    class FakeService2:
        def __init__(self, db, cache):
            pass

        async def verify_name_update(self, token, user_id):
            return {"success": False, "message": "nope"}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService2)
    res2 = await auth_ctrl.handle_verify_admin_name_update_controller(token='t', user_id='u', db=None, cache=None)
    assert isinstance(res2, RedirectResponse)
    assert 'status=error' in res2.headers.get('location')

    class FakeService3:
        def __init__(self, db, cache):
            pass

        async def verify_name_update(self, token, user_id):
            raise HTTPException(status_code=400, detail='bad')

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService3)
    res3 = await auth_ctrl.handle_verify_admin_name_update_controller(token='t', user_id='u', db=None, cache=None)
    assert isinstance(res3, RedirectResponse)
    assert 'status=error' in res3.headers.get('location')
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from jose import ExpiredSignatureError

import app.controllers.authentication_controller as auth_ctrl
from app.schemas.authentication_request import UpdateEmailVerifyTokenRequest, AdminUpdateRequest


@pytest.mark.asyncio
async def test_handle_search_admins_success(monkeypatch):
    async def fake_search(db, q):
        return [{'user_id': 'u1'}]

    monkeypatch.setattr('app.db.repository.user_repository.search_admins', AsyncMock(side_effect=fake_search))

    resp = await auth_ctrl.handle_search_admins_controller('query', AsyncMock())
    assert resp.status_code == 200
    assert 'admins' in resp.body.decode()


@pytest.mark.asyncio
async def test_handle_search_admins_failure(monkeypatch):
    monkeypatch.setattr('app.db.repository.user_repository.search_admins', AsyncMock(side_effect=Exception('boom')))
    resp = await auth_ctrl.handle_search_admins_controller('q', AsyncMock())
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_handle_update_admin_controller_no_auth():
    req = SimpleNamespace()
    req.state = SimpleNamespace(user=None)
    resp = await auth_ctrl.handle_update_admin_controller('id', AdminUpdateRequest(email='a@b.com'), AsyncMock(), None, req)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_handle_update_admin_controller_success(monkeypatch):
    class FakeUpdateService:
        def __init__(self, db, cache): pass
        async def update_admin_details(self, aid, ud, caller_role, caller_id):
            return {'success': True, 'data': {'user_id': aid}, 'status_code': 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeUpdateService)
    req = SimpleNamespace(); req.state = SimpleNamespace(user={'role': 'SUPER_ADMIN', 'sub': 'u1'})
    res = await auth_ctrl.handle_update_admin_controller('id', AdminUpdateRequest(email='x@x.com'), AsyncMock(), None, req)
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_handle_verify_admin_name_update_redirects(monkeypatch):
    class FakeService:
        def __init__(self, db, cache): pass
        async def verify_name_update(self, token, user_id):
            return {'success': True}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    # success
    res = await auth_ctrl.handle_verify_admin_name_update_controller('t', 'u', AsyncMock(), None)
    assert isinstance(res, RedirectResponse)
    assert 'status=success' in res.headers['location']

    # return failure dict
    class FakeFailService:
        def __init__(self, db, cache): pass
        async def verify_name_update(self, token, user_id):
            return {'success': False, 'message': 'err'}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeFailService)
    res2 = await auth_ctrl.handle_verify_admin_name_update_controller('t', 'u', AsyncMock(), None)
    assert isinstance(res2, RedirectResponse)
    assert 'status=error' in res2.headers['location']


@pytest.mark.asyncio
async def test_handle_verify_admin_name_update_http_exception(monkeypatch):
    class FakeService:
        def __init__(self, db, cache): pass
        async def verify_name_update(self, token, user_id):
            raise HTTPException(status_code=400, detail='x')

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    res = await auth_ctrl.handle_verify_admin_name_update_controller('t', 'u', AsyncMock(), None)
    assert isinstance(res, RedirectResponse)
    assert 'status=error' in res.headers['location']


@pytest.mark.asyncio
async def test_handle_verify_admin_phone_update_redirects(monkeypatch):
    class FakeService:
        def __init__(self, db, cache): pass
        async def verify_phone_update(self, token, user_id):
            return {'success': True}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    res = await auth_ctrl.handle_verify_admin_phone_update_controller('t', 'u', AsyncMock(), None)
    assert isinstance(res, RedirectResponse)
    assert 'status=success' in res.headers['location']

    class FakeServiceFail:
        def __init__(self, db, cache): pass
        async def verify_phone_update(self, token, user_id):
            return {'success': False, 'message': 'err'}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeServiceFail)
    res2 = await auth_ctrl.handle_verify_admin_phone_update_controller('t', 'u', AsyncMock(), None)
    assert 'status=error' in res2.headers['location']


@pytest.mark.asyncio
async def test_handle_verify_admin_email_update_controller(monkeypatch):
    class FakeService:
        def __init__(self, db, cache): pass
        async def verify_email_update(self, user_data):
            return {'success': True, 'status_code': 200}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    req = UpdateEmailVerifyTokenRequest(user_id='u', token='t', new_email='n@e.com')
    res = await auth_ctrl.handle_verify_admin_email_update_controller(req, AsyncMock(), None)
    assert isinstance(res, JSONResponse)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_handle_approve_email_update_dashboard_redirects(monkeypatch):
    class FakeService:
        def __init__(self, db, cache): pass
        async def approve_email_update(self, token, user_id):
            return {'success': True, 'data': {'new_email': 'n@e.com'}}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    res = await auth_ctrl.handle_approve_email_update_controller('t', 'u', AsyncMock(), None)
    assert isinstance(res, RedirectResponse)
    assert 'email_transfer_approved' in res.headers['location']


@pytest.mark.asyncio
async def test_handle_complete_email_update_controller_flow(monkeypatch):
    class FakeService:
        def __init__(self, db, cache): pass
        async def verify_email_update(self, data):
            return {'success': True}

    monkeypatch.setattr(auth_ctrl, 'UpdateAdminService', FakeService)
    res = await auth_ctrl.handle_complete_email_update_controller('t', 'u', 'a@b.com', AsyncMock(), None)
    assert isinstance(res, RedirectResponse)
    assert 'email_updated' in res.headers['location']
