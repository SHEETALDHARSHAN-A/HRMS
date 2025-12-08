import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, status

from app.services.admin_service.update_admin_service import UpdateAdminService
from app.schemas.authentication_request import AdminUpdateRequest, UpdateEmailVerifyTokenRequest


class SimpleUser:
    def __init__(self, user_id="u1", email="a@a.com", first_name="Old", last_name="Name", role="ADMIN", phone_number=None):
        self.user_id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.phone_number = phone_number


@pytest.mark.asyncio
async def test_update_admin_details_user_not_found(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=None))

    svc = UpdateAdminService(db=db, cache=cache)

    with pytest.raises(HTTPException) as exc:
        await svc.update_admin_details("does-not-exist", AdminUpdateRequest())

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


    @pytest.mark.asyncio
    async def test_update_admin_details_no_caller_role_forbidden(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        user = SimpleUser(user_id="u26", role="ADMIN")
        monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

        svc = UpdateAdminService(db=db, cache=cache)
        with pytest.raises(Exception) as exc:
            await svc.update_admin_details("u26", AdminUpdateRequest())

        assert getattr(exc.value, 'status_code', None) == status.HTTP_403_FORBIDDEN


    @pytest.mark.asyncio
    async def test_hr_cannot_change_roles(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        user = SimpleUser(user_id="u27", role="HR")
        monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

        svc = UpdateAdminService(db=db, cache=cache)
        with pytest.raises(Exception) as exc:
            await svc.update_admin_details("u27", AdminUpdateRequest(role="ADMIN"), caller_role="HR")

        assert getattr(exc.value, 'status_code', None) == status.HTTP_403_FORBIDDEN


    @pytest.mark.asyncio
    async def test_role_change_update_returns_none_raises_404(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        user = SimpleUser(user_id="u28", role="ADMIN")
        monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
        # update_user_details returns None
        monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=None))

        svc = UpdateAdminService(db=db, cache=cache)
        with pytest.raises(Exception) as exc:
            await svc.update_admin_details("u28", AdminUpdateRequest(role="HR"), caller_role="SUPER_ADMIN")

        assert getattr(exc.value, 'status_code', None) == status.HTTP_404_NOT_FOUND


    @pytest.mark.asyncio
    async def test_role_change_email_exception_is_suppressed(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        user = SimpleUser(user_id="u29", role="ADMIN")
        updated_user = SimpleUser(user_id="u29", role="HR")
        monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))

        cache.smembers = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()

        # Make the send function raise; service should catch and continue
        monkeypatch.setattr("app.utils.email_utils.send_admin_role_change_email", AsyncMock(side_effect=Exception("mail fail")))

        svc = UpdateAdminService(db=db, cache=cache)
        res = await svc.update_admin_details("u29", AdminUpdateRequest(role="HR"), caller_role="SUPER_ADMIN")

        assert res.get("success") is True


    @pytest.mark.asyncio
    async def test_phone_only_update_initiates_flow_success(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        user = SimpleUser(user_id="u30", phone_number="000")
        monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

        # Patch phone email sender to succeed
        monkeypatch.setattr("app.services.admin_service.update_admin_service.send_phone_update_verification_link", AsyncMock(return_value=True))
        cache.set = AsyncMock()

        svc = UpdateAdminService(db=db, cache=cache)
        res = await svc.update_admin_details("u30", AdminUpdateRequest(phone_number="111"), caller_role="SUPER_ADMIN")

        assert res.get("success") is True
        assert res.get("status_code") == status.HTTP_202_ACCEPTED
        assert res.get("data").get("verification_status") == "PENDING_PHONE_CONFIRMATION"


    @pytest.mark.asyncio
    async def test_name_change_email_send_failure_rolls_back_cache(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        user = SimpleUser(user_id="u31", first_name="Old", last_name="N")
        monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
        # Fail name email send
        monkeypatch.setattr("app.services.admin_service.update_admin_service.send_name_update_verification_link", AsyncMock(return_value=False))
        cache.set = AsyncMock()
        cache.delete = AsyncMock()

        svc = UpdateAdminService(db=db, cache=cache)
        with pytest.raises(Exception) as exc:
            await svc.update_admin_details("u31", AdminUpdateRequest(first_name="New"), caller_role="SUPER_ADMIN")

        assert getattr(exc.value, 'status_code', None) == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert cache.delete.called


    @pytest.mark.asyncio
    async def test_approve_email_update_invalid_token_returns_success(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)

        svc = UpdateAdminService(db=db, cache=cache)
        res = await svc.approve_email_update("bad", "u32")

        assert res.get("success") is True
        assert res.get("status_code") == status.HTTP_200_OK


    @pytest.mark.asyncio
    async def test_verify_name_update_invalid_token_returns_success(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)

        svc = UpdateAdminService(db=db, cache=cache)
        res = await svc.verify_name_update("bad", "u33")

        assert res.get("success") is True


    @pytest.mark.asyncio
    async def test_verify_email_update_integrity_failure(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()

        token = "tok-int"
        # cached data has different new_email to trigger integrity check
        payload = {"user_id": "u34", "type": "email_update", "new_email": "other@x.com", "name_updates": {}}
        cache.get = AsyncMock(return_value=json.dumps(payload))
        svc = UpdateAdminService(db=db, cache=cache)
        input_obj = UpdateEmailVerifyTokenRequest(user_id="u34", token=token, new_email="mismatch@x.com")

        with pytest.raises(Exception) as exc:
            await svc.verify_email_update(input_obj, is_api_request=True)

        assert getattr(exc.value, 'status_code', None) == status.HTTP_400_BAD_REQUEST


    @pytest.mark.asyncio
    async def test_update_admin_email_send_failure_raises(monkeypatch):
        db = MagicMock()
        cache = AsyncMock()
        cache.set = AsyncMock()

        # Make the send function raise
        monkeypatch.setattr("app.services.admin_service.update_admin_service.send_email_update_verification_link", AsyncMock(side_effect=Exception("smtp fail")))

        svc = UpdateAdminService(db=db, cache=cache)
        with pytest.raises(Exception) as exc:
            await svc.update_admin_email("u35", "err@x.com", db)

        assert getattr(exc.value, 'status_code', None) == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_update_admin_details_insufficient_permissions(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    # target user is SUPER_ADMIN, caller is HR -> forbidden
    target = SimpleUser(role="SUPER_ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=target))

    svc = UpdateAdminService(db=db, cache=cache)

    with pytest.raises(HTTPException) as exc:
        await svc.update_admin_details("u1", AdminUpdateRequest(), caller_role="HR")

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_admin_details_name_change_triggers_email_and_cache(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u2", first_name="Old", last_name="Name", role="ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    # Ensure generate_token returns predictable token
    monkeypatch.setattr("app.services.admin_service.update_admin_service.generate_token", lambda: "tok-123")

    # Patch cache.set and email sender
    cache.set = AsyncMock()
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_name_update_verification_link", AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)

    req = AdminUpdateRequest(first_name="New")
    res = await svc.update_admin_details("u2", req, caller_role="SUPER_ADMIN")

    assert res.get("success") is True
    assert res.get("status_code") == status.HTTP_202_ACCEPTED
    data = res.get("data")
    assert data.get("verification_status") == "PENDING_NAME_CONFIRM"

    # cache.set must have been called with verify_update:tok-123 key
    assert cache.set.called
    key_arg = cache.set.call_args[0][0]
    assert key_arg.startswith(svc.VERIFY_KEY_PREFIX + "tok-123") or (svc.VERIFY_KEY_PREFIX in key_arg)


@pytest.mark.asyncio
async def test_verify_email_update_missing_token_returns_error(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)

    svc = UpdateAdminService(db=db, cache=cache)

    input_obj = UpdateEmailVerifyTokenRequest(user_id="u3", token="nope", new_email="new@ex.com")
    res = await svc.verify_email_update(input_obj, is_api_request=False)

    assert isinstance(res, dict)
    assert res.get("status_code") == status.HTTP_400_BAD_REQUEST
    assert res.get("success") is False


@pytest.mark.asyncio
async def test_update_admin_details_role_change_revokes_jtis_and_sends_email(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u9", email="old@x.com", first_name="A", last_name="B", role="ADMIN")
    updated_user = SimpleUser(user_id="u9", email="old@x.com", first_name="A", last_name="B", role="SUPER_ADMIN")

    # Initial lookup returns user, update_user_details persists and returns updated_user
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))

    # Simulate stored JTIs for both refresh and access sets
    cache.smembers = AsyncMock(side_effect=lambda k: {b"rjti1", b"rjti2"} if "refresh" in k else {b"ajti1"})
    cache.delete = AsyncMock()
    cache.set = AsyncMock()

    # Patch JTI blocklist adder and role-change email sender
    mock_add_jti = AsyncMock()
    monkeypatch.setattr("app.services.admin_service.update_admin_service.add_jti_to_blocklist", mock_add_jti)
    monkeypatch.setattr("app.utils.email_utils.send_admin_role_change_email", AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)

    req = AdminUpdateRequest(role="SUPER_ADMIN")
    res = await svc.update_admin_details("u9", req, caller_role="SUPER_ADMIN", caller_id="caller-x")

    assert res.get("success") is True
    assert res.get("status_code") == 200
    assert res.get("data", {}).get("new_role") == "SUPER_ADMIN"
    # Ensure JTI blocklist was attempted
    assert mock_add_jti.called


@pytest.mark.asyncio
async def test_verify_phone_update_success(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    payload = {
        "user_id": "u10",
        "type": "phone_update",
        "new_phone_number": "12345",
        "old_phone_number": ""
    }

    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.delete = AsyncMock()

    updated_user = SimpleUser(user_id="u10", phone_number="12345")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))

    svc = UpdateAdminService(db=db, cache=cache)

    res = await svc.verify_phone_update("token-xyz", "u10")

    assert isinstance(res, dict) or hasattr(res, "get")
    assert res.get("success") is True
    assert res.get("data").get("phone_number") == "12345"
    assert cache.delete.called


@pytest.mark.asyncio
async def test_verify_name_update_success(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    payload = {"user_id": "u11", "type": "name_update", "updates": {"first_name": "New", "last_name": "Name"}}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.delete = AsyncMock()

    updated_user = SimpleUser(user_id="u11", first_name="New", last_name="Name", email="u11@x.com")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))
    mock_notify = AsyncMock()
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_name_update_success_notification", mock_notify)

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.verify_name_update("tok-n", "u11")

    assert res.get("success") is True
    assert res.get("data")["first_name"] == "New"
    assert mock_notify.called


@pytest.mark.asyncio
async def test_approve_email_update_success(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    payload = {"user_id": "u12", "type": "email_update_approval", "old_email": "old@x.com", "new_email": "new@x.com", "admin_first_name": "A", "admin_full_name": "A B"}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    monkeypatch.setattr("app.utils.email_utils.send_email_update_verification_link", AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.approve_email_update("tok-approve", "u12")

    assert res.get("success") is True
    assert res.get("data").get("verification_status") == "PENDING_NEW_EMAIL_CONFIRM"


@pytest.mark.asyncio
async def test_verify_email_update_success(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    token = "tok-final"
    payload = {"user_id": "u13", "type": "email_update", "new_email": "final@x.com", "name_updates": {}}
    # cache returns payload for token_key
    async def cache_get(key):
        if key.startswith("verify_update:"):
            return json.dumps(payload)
        if key == f"api_verify:{token}":
            return None
        return None

    cache.get = AsyncMock(side_effect=cache_get)
    cache.smembers = AsyncMock(return_value={b"j1"})
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    user = SimpleUser(user_id="u13", email="old@x.com")
    updated_user = SimpleUser(user_id="u13", email="final@x.com")

    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.add_jti_to_blocklist", AsyncMock())

    svc = UpdateAdminService(db=db, cache=cache)
    input_obj = UpdateEmailVerifyTokenRequest(user_id="u13", token=token, new_email="final@x.com")
    res = await svc.verify_email_update(input_obj, is_api_request=False)

    assert res.get("success") is True
    assert res.get("data")["new_email"] == "final@x.com"


@pytest.mark.asyncio
async def test_update_admin_details_admin_assign_superadmin_forbidden(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    # Caller is ADMIN trying to assign SUPER_ADMIN
    user = SimpleUser(user_id="u14", role="ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(Exception) as exc:
        await svc.update_admin_details("u14", AdminUpdateRequest(role="SUPER_ADMIN"), caller_role="ADMIN")

    assert getattr(exc.value, 'status_code', None) == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_admin_details_admin_modify_superadmin_forbidden(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    # Caller is ADMIN but target is SUPER_ADMIN -> forbidden
    user = SimpleUser(user_id="u15", role="SUPER_ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(Exception) as exc:
        await svc.update_admin_details("u15", AdminUpdateRequest(role="ADMIN"), caller_role="ADMIN")

    assert getattr(exc.value, 'status_code', None) == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_admin_details_role_change_db_failure(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u16", role="ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    # Simulate DB update failure
    async def raise_exc(*a, **k):
        raise Exception("db unavailable")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(side_effect=Exception("db unavailable")))

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(Exception) as exc:
        await svc.update_admin_details("u16", AdminUpdateRequest(role="HR"), caller_role="SUPER_ADMIN")

    assert getattr(exc.value, 'status_code', None) == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_role_change_revokes_refresh_and_access_jtis(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u40", role="ADMIN")
    updated_user = SimpleUser(user_id="u40", role="HR")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))

    # Return different types for refresh and access sets (bytes and str)
    async def smembers(key):
        if key.startswith("active_refresh_jtis"):
            return {b"rjti1", b"rjti2"}
        if key.startswith("active_access_jtis"):
            return {"ajti1", b"ajti2"}
        return None

    cache.smembers = AsyncMock(side_effect=smembers)
    cache.delete = AsyncMock()
    cache.set = AsyncMock()

    calls = []
    async def fake_add_jti(jti, cache_obj, lifespan):
        calls.append(jti)

    monkeypatch.setattr("app.services.admin_service.update_admin_service.add_jti_to_blocklist", AsyncMock(side_effect=fake_add_jti))

    monkeypatch.setattr("app.utils.email_utils.send_admin_role_change_email", AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.update_admin_details("u40", AdminUpdateRequest(role="HR"), caller_role="SUPER_ADMIN")

    assert res.get("success") is True
    # add_jti_to_blocklist should have been called for each JTI (decoded where necessary)
    assert len(calls) >= 3


@pytest.mark.asyncio
async def test_role_change_add_jti_exceptions_are_logged(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u41", role="ADMIN")
    updated_user = SimpleUser(user_id="u41", role="HR")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(return_value=updated_user))

    cache.smembers = AsyncMock(return_value={b"r1"})
    cache.delete = AsyncMock()
    cache.set = AsyncMock()

    # make add_jti_to_blocklist raise for one jti
    async def raise_once(jti, cache_obj, lifespan):
        raise Exception("boom")

    monkeypatch.setattr("app.services.admin_service.update_admin_service.add_jti_to_blocklist", AsyncMock(side_effect=raise_once))
    monkeypatch.setattr("app.utils.email_utils.send_admin_role_change_email", AsyncMock(return_value=True))

    svc = UpdateAdminService(db=db, cache=cache)
    # should not raise despite add_jti_to_blocklist raising
    res = await svc.update_admin_details("u41", AdminUpdateRequest(role="HR"), caller_role="SUPER_ADMIN")
    assert res.get("success") is True


@pytest.mark.asyncio
async def test_update_admin_email_stores_cache_with_uuid(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    cache.set = AsyncMock()

    # Make uuid predictable
    class DummyUUID:
        def __str__(self):
            return "deadbeef-0000-0000-0000-deadbeef0000"

    monkeypatch.setattr("app.services.admin_service.update_admin_service.uuid4", lambda: DummyUUID())
    # patch send to not raise
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_email_update_verification_link", AsyncMock())

    svc = UpdateAdminService(db=db, cache=cache)
    res = await svc.update_admin_email("u50", "x50@x.com", db)

    assert res.get("success") is True
    # cache.set must have been called with email_update:<uuid>
    assert cache.set.called
    key = cache.set.call_args[0][0]
    assert key.startswith("email_update:") and "deadbeef" in key


@pytest.mark.asyncio
async def test_initiate_phone_update_email_failure(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u17", role="ADMIN", phone_number="111")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    # Phone-only update: make send_phone_update_verification_link fail
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_phone_update_verification_link", AsyncMock(return_value=False))
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(Exception) as exc:
        await svc.update_admin_details("u17", AdminUpdateRequest(phone_number="222"), caller_role="SUPER_ADMIN")

    assert getattr(exc.value, 'status_code', None) == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_email_change_old_email_send_failure(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    user = SimpleUser(user_id="u18", email="old@ex.com", role="ADMIN")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    # Make sending to old email fail
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_email_change_transfer_notification", AsyncMock(return_value=False))
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(Exception) as exc:
        await svc.update_admin_details("u18", AdminUpdateRequest(new_email="new@ex.com"), caller_role="SUPER_ADMIN")

    assert getattr(exc.value, 'status_code', None) == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_approve_email_update_new_email_send_failure(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()

    payload = {"user_id": "u19", "type": "email_update_approval", "old_email": "old@x.com", "new_email": "new@x.com"}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    # Fail to send to new email (patch module-level reference used by the service)
    monkeypatch.setattr("app.services.admin_service.update_admin_service.send_email_update_verification_link", AsyncMock(return_value=False))

    svc = UpdateAdminService(db=db, cache=cache)
    with pytest.raises(Exception) as exc:
        await svc.approve_email_update("tok-approve2", "u19")

    assert getattr(exc.value, 'status_code', None) == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_verify_email_update_api_raises_on_missing_token(monkeypatch):
    db = MagicMock()
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)

    svc = UpdateAdminService(db=db, cache=cache)
    input_obj = UpdateEmailVerifyTokenRequest(user_id="u20", token="none", new_email="x@x.com")

    with pytest.raises(Exception) as exc:
        await svc.verify_email_update(input_obj, is_api_request=True)

    assert getattr(exc.value, 'status_code', None) == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_verify_email_update_duplicate_key_handling(monkeypatch):
    db = MagicMock()
    db.rollback = AsyncMock()
    cache = AsyncMock()

    token = "tok-dup"
    payload = {"user_id": "u21", "type": "email_update", "new_email": "dup@x.com", "name_updates": {}}
    cache.get = AsyncMock(return_value=json.dumps(payload))
    cache.smembers = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()

    user = SimpleUser(user_id="u21", email="old@x.com")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.get_user_by_id", AsyncMock(return_value=user))

    # Simulate unique constraint DB error
    class DummyDBExc(Exception):
        pass

    db_exc = Exception("duplicate key value violates unique constraint")
    monkeypatch.setattr("app.services.admin_service.update_admin_service.update_user_details", AsyncMock(side_effect=db_exc))

    svc = UpdateAdminService(db=db, cache=cache)
    input_obj = UpdateEmailVerifyTokenRequest(user_id="u21", token=token, new_email="dup@x.com")

    with pytest.raises(Exception) as exc:
        await svc.verify_email_update(input_obj, is_api_request=True)

    # Expect a 409 conflict raised by the service
    assert getattr(exc.value, 'status_code', None) == status.HTTP_409_CONFLICT
