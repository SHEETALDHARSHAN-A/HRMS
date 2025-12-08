import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, status

from app.services.admin_service.update_admin_service import UpdateAdminService
from app.schemas.authentication_request import AdminUpdateRequest, UpdateEmailVerifyTokenRequest


class SimpleUser:
    def __init__(self, user_id="ux", email="a@a.com", first_name="Old", last_name="Name", role="ADMIN", phone_number=None):
        self.user_id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.phone_number = phone_number


@pytest.mark.asyncio
async def test_no_fields_updated_returns_no_changes(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u100", first_name="Same", last_name="Same", role="ADMIN", phone_number=None)
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    svc = UpdateAdminService(db=db, cache=cache)
    # caller must have permission; use SUPER_ADMIN to allow no-op
    res = await svc.update_admin_details("u100", AdminUpdateRequest(), caller_role="SUPER_ADMIN")

    assert res.get("success") is True
    assert res.get("data") is None


@pytest.mark.asyncio
async def test_admin_assign_invalid_role_forbidden(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u101", role="ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    svc = UpdateAdminService(db=db, cache=cache)
    # Pydantic will validate role values; create a simple object to simulate an invalid role request
    class FakeInput:
        def __init__(self, role):
            self.role = role
            self.first_name = None
            self.last_name = None
            self.new_email = None
            self.phone_number = None
            self.expiration_days = None

    with pytest.raises(HTTPException) as exc:
        await svc.update_admin_details("u101", FakeInput(role="FOO"), caller_role="ADMIN")

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_verify_name_update_type_mismatch_and_empty_updates(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    # type mismatch: cached type is email_update -> should return success
    payload = {"user_id": "u102", "type": "email_update", "updates": {}}
    cache.get = AsyncMock(return_value=json.dumps(payload))

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.verify_name_update("tok", "u102")

    assert res.get("success") is True

    # now test empty updates path which triggers cache.delete and success
    payload2 = {"user_id": "u103", "type": "name_update", "updates": {}}
    cache.get = AsyncMock(return_value=json.dumps(payload2))
    cache.delete = AsyncMock()

    svc2 = UpdateAdminService(db=db, cache=cache)
    res2 = await svc2.verify_name_update("tok2", "u103")
    assert res2.get("success") is True
    assert cache.delete.called


@pytest.mark.asyncio
async def test_verify_phone_update_invalid_token_returns_success(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.verify_phone_update("nope", "u104")

    assert res.get("success") is True
    assert res.get("status_code") == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_approve_email_update_incomplete_data_raises(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    # payload missing old_email
    payload = {"user_id": "u105", "type": "email_update_approval", "new_email": "n@x.com"}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.delete = AsyncMock()

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(HTTPException) as exc:
        await svc.approve_email_update("tok3", "u105")

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert cache.delete.called


@pytest.mark.asyncio
async def test_verify_email_update_user_not_found_after_temp_access(monkeypatch):
    db = MagicMock()
    db.rollback = AsyncMock()
    cache = AsyncMock()

    token = "tok404"
    payload = {"user_id": "u106", "type": "email_update", "new_email": "new@x.com", "name_updates": {}}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    # get_user_by_id returns None -> should delete token and raise 404
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=None))

    svc = UpdateAdminService(db=db, cache=cache)
    input_obj = UpdateEmailVerifyTokenRequest(user_id="u106", token=token, new_email="new@x.com")

    with pytest.raises(HTTPException) as exc:
        await svc.verify_email_update(input_obj, is_api_request=True)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert cache.delete.called


@pytest.mark.asyncio
async def test_role_change_smembers_raises_is_handled(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u200", role="ADMIN", email="u@x.com")
    updated_user = SimpleUser(user_id="u200", role="HR", email="u@x.com")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))

    # smembers raises for any key to simulate redis failure; service should handle this
    async def raise_smembers(k):
        raise Exception("redis down")

    cache.smembers = AsyncMock(side_effect=raise_smembers)
    cache.delete = AsyncMock()
    cache.set = AsyncMock()

    monkeypatch.setattr("app.services.admin_service.update_admin_service.add_jti_to_blocklist", AsyncMock())
    monkeypatch.setattr("app.utils.email_utils.send_admin_role_change_email", AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.update_admin_details("u200", AdminUpdateRequest(role="HR"), caller_role="SUPER_ADMIN")

    assert res.get("success") is True
    # Even though smembers raised, the function should have attempted to set the role and return success


@pytest.mark.asyncio
async def test_verify_email_update_preserving_session_deletes_session(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    token = "tok-preserve"
    payload = {"user_id": "u300", "type": "email_update", "new_email": "preserve@x.com", "name_updates": {}}

    # cache.get returns token payload for verify key, and returns a truthy value for preserving session key
    async def cache_get(key):
        if key == f"verify_update:{token}":
            return json.dumps(payload)
        if key == f"preserving_session:{payload['user_id']}":
            return "1"
        return None

    cache.get = AsyncMock(side_effect=cache_get)
    cache.smembers = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    user = SimpleUser(user_id=payload["user_id"], email="old@x.com")
    updated_user = SimpleUser(user_id=payload["user_id"], email=payload["new_email"]) 

    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.add_jti_to_blocklist", AsyncMock())

    svc = UpdateAdminService(db=db, cache=cache)
    input_obj = UpdateEmailVerifyTokenRequest(user_id=payload["user_id"], token=token, new_email=payload["new_email"])

    res = await svc.verify_email_update(input_obj, is_api_request=False)

    assert res.get("success") is True
    # Ensure email_update_success flag was set
    assert any(call.args[0].startswith("email_update_success:") for call in cache.set.call_args_list)
    # Ensure preserving session key was deleted
    assert any(call.args[0] == f"preserving_session:{payload['user_id']}" for call in cache.delete.call_args_list)


@pytest.mark.asyncio
async def test_verify_name_update_db_returns_none_raises(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    payload = {"user_id": "u400", "type": "name_update", "updates": {"first_name": "X"}}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.delete = AsyncMock()

    # Simulate DB update returning None
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=None))

    svc = UpdateAdminService(db=db, cache=cache)

    with pytest.raises(HTTPException) as exc:
        await svc.verify_name_update("tkn", "u400")

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
