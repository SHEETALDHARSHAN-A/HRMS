import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.admin_service.update_admin_service import UpdateAdminService
from app.schemas.authentication_request import AdminUpdateRequest


class SimpleUser:
    def __init__(self, user_id="ux", email="a@a.com", first_name="Old", last_name="Name", role="ADMIN", phone_number=None):
        self.user_id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.phone_number = phone_number


@pytest.mark.asyncio
async def test_phone_only_update_returns_pending(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u500", phone_number="")
    monkeypatch.setattr('app.services.admin_service.update_admin_service.get_user_by_id', AsyncMock(return_value=user))
    # send_phone_update_verification_link should be called; we will patch it to return True
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_phone_update_verification_link', AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)
    input_obj = AdminUpdateRequest(first_name=None, last_name=None, new_email=None, phone_number='9000000000')
    res = await svc.update_admin_details('u500', input_obj, caller_role='SUPER_ADMIN')

    assert res['success'] is True
    assert res['status_code'] == 202
    assert 'Phone number update pending confirmation' in res['message']
    # cache set called because we generate a token key in _initiate_phone_update_flow
    assert cache.set.called

@pytest.mark.asyncio
async def test_update_admin_details_email_change_initiates_cache_and_notifications(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    # Setup user
    user = SimpleUser(user_id="u600", email="old@x.com", first_name="Old", last_name="L", role="ADMIN")
    monkeypatch.setattr('app.services.admin_service.update_admin_service.get_user_by_id', AsyncMock(return_value=user))
    # Mock send_email_change_transfer_notification to return True
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_email_change_transfer_notification', AsyncMock(return_value=True))
    cache.set = AsyncMock()

    svc = UpdateAdminService(db=db, cache=cache)
    # Input with new_email should take email change path
    from app.schemas.authentication_request import AdminUpdateRequest
    inp = AdminUpdateRequest(new_email='new@x.com')
    res = await svc.update_admin_details('u600', inp, caller_role='SUPER_ADMIN')
    assert res.get('success') is True
    # token key set in cache
    assert cache.set.called

@pytest.mark.asyncio
async def test_update_admin_email_uses_cache_and_send(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_email_update_verification_link', AsyncMock(return_value=True))
    cache.set = AsyncMock()
    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.update_admin_email('u700', 'new@x.com', db=db)
    assert res['data']['verification_sent'] is True
    assert cache.set.called

@pytest.mark.asyncio
async def test_initiate_phone_update_flow_fails_on_email_send(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    user = SimpleUser(user_id='u800', email='a@b.com')
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_phone_update_verification_link', AsyncMock(return_value=False))
    svc = UpdateAdminService(db=db, cache=cache)
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await svc._initiate_phone_update_flow(user=user, new_phone='9999', current_phone='')

@pytest.mark.asyncio
async def test_approve_email_update_success_sets_api_and_sends(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    token = 'tokOK'
    payload = {"user_id": "u900", "type": "email_update_approval", "new_email": "n@x.com", "old_email": "o@x.com", "admin_first_name": "Old"}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_email_update_verification_link', AsyncMock(return_value=True))
    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.approve_email_update(token, 'u900')
    assert res['success'] is True
    assert cache.set.called


@pytest.mark.asyncio
async def test_initiate_phone_update_flow_calls_send_and_sets_cache(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    user = SimpleUser(user_id='u800', email='a@b.com')
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_phone_update_verification_link', AsyncMock(return_value=True))
    svc = UpdateAdminService(db=db, cache=cache)
    payload = await svc._initiate_phone_update_flow(user=user, new_phone='9999', current_phone='')
    assert payload['verification_status'] == 'PENDING_PHONE_CONFIRMATION'
    assert cache.set.called


@pytest.mark.asyncio
async def test_initiate_phone_update_flow_failure_raises(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    user = SimpleUser(user_id='u801', email='a@b.com')
    monkeypatch.setattr('app.services.admin_service.update_admin_service.send_phone_update_verification_link', AsyncMock(return_value=False))
    svc = UpdateAdminService(db=db, cache=cache)
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await svc._initiate_phone_update_flow(user=user, new_phone='9999', current_phone='')


@pytest.mark.asyncio
async def test_verify_phone_update_success(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    svc = UpdateAdminService(db=db, cache=cache)
    token_key = 'verify_update:tok'
    cache.get = AsyncMock(return_value=json.dumps({'user_id': 'u900', 'type': 'phone_update', 'new_phone_number': '9999'}))
    cache.delete = AsyncMock()
    # Mock update_user_details to return a user object
    updated_user = SimpleUser(user_id='u900', phone_number='9999')
    monkeypatch.setattr('app.services.admin_service.update_admin_service.update_user_details', AsyncMock(return_value=updated_user))
    res = await svc.verify_phone_update('tok', 'u900')
    assert res['success'] is True
    assert cache.delete.called


@pytest.mark.asyncio
async def test_verify_phone_update_invalid_token_returns_message(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    svc = UpdateAdminService(db=db, cache=cache)
    cache.get = AsyncMock(return_value=None)
    res = await svc.verify_phone_update('tokx', 'u900')
    assert res['success'] is True
    assert res['data'] is None
