import json
import pytest
from unittest.mock import AsyncMock
from app.services.admin_service.update_admin_service import UpdateAdminService
from app.utils.standard_response_utils import ResponseBuilder

@pytest.mark.asyncio
async def test_verify_phone_update_token_missing(fake_db, fake_cache):
    fake_cache.get = AsyncMock(return_value=None)
    svc = UpdateAdminService(fake_db, fake_cache)
    res = await svc.verify_phone_update("anytoken", "user1")
    assert res["success"] is True
    assert res["status_code"] == 200

@pytest.mark.asyncio
async def test_verify_phone_update_type_mismatch(fake_db, fake_cache):
    payload = {"type": "name_update", "user_id": "user1"}
    fake_cache.get = AsyncMock(return_value=json.dumps(payload))
    svc = UpdateAdminService(fake_db, fake_cache)
    res = await svc.verify_phone_update("token1", "user1")
    assert res["success"] is True
    assert res["status_code"] == 200

@pytest.mark.asyncio
async def test_verify_phone_update_success_updates_db_and_clears_cache(monkeypatch, fake_db, fake_cache):
    payload = {"type": "phone_update", "user_id": "user1", "new_phone_number": "+123"}
    fake_cache.get = AsyncMock(return_value=json.dumps(payload))
    # Mock update_user_details to return a truthy value
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=object()))
    fake_cache.delete = AsyncMock()
    svc = UpdateAdminService(fake_db, fake_cache)
    res = await svc.verify_phone_update("token1", "user1")
    assert res["success"] is True
    assert res["data"]["phone_number"] == "+123"
    fake_cache.delete.assert_awaited()

@pytest.mark.asyncio
async def test_verify_name_update_invalid_and_success(monkeypatch, fake_db, fake_cache):
    svc = UpdateAdminService(fake_db, fake_cache)
    # missing token
    fake_cache.get = AsyncMock(return_value=None)
    res = await svc.verify_name_update("tok", "u1")
    assert res["success"] is True

    # mismatched type
    fake_cache.get = AsyncMock(return_value=json.dumps({"type": "phone_update", "user_id": "u1"}))
    res2 = await svc.verify_name_update("tok2", "u1")
    assert res2["success"] is True

    # success path
    cached = {"type": "name_update", "user_id": "u1", "updates": {"first_name": "New", "last_name": "Name"}}
    fake_cache.get = AsyncMock(return_value=json.dumps(cached))
    # mock update_user_details to return an object with first_name/last_name/email
    class UserObj:
        def __init__(self):
            self.first_name = "New"
            self.last_name = "Name"
            self.email = "u1@example.com"
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=UserObj()))
    # mock send_name_update_success_notification
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_name_update_success_notification", AsyncMock(return_value=True))
    fake_cache.delete = AsyncMock()
    res3 = await svc.verify_name_update("tok3", "u1")
    assert res3["success"] is True
    assert res3["data"]["first_name"] == "New"
    fake_cache.delete.assert_awaited()
