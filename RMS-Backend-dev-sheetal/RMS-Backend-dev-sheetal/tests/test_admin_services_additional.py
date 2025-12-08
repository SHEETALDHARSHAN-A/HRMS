import json
import uuid
import datetime
import pytest

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.schemas.authentication_request import AdminInviteRequest
from app.services.admin_service.invite_admin_service import InviteAdminService
from app.services.admin_service.complete_admin_setup_service import CompleteAdminSetupService


class FakeDB:
    def __init__(self):
        self.deleted = []
    def add(self, obj):
        return None
    async def commit(self):
        return None
    async def refresh(self, obj):
        if getattr(obj, "invitation_id", None) is None:
            obj.invitation_id = uuid.uuid4()
        if getattr(obj, "expires_at", None) is None:
            obj.expires_at = datetime.datetime.utcnow()
        return None
    async def delete(self, obj):
        self.deleted.append(obj)
        return None
    async def execute(self, query):
        class Result:
            def scalar_one_or_none(self_inner):
                return None
        return Result()


@pytest.mark.asyncio
async def test_generate_admin_invite_expiration_days_variants(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()

    class SimpleInvitation:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            if not hasattr(self, 'invitation_id'):
                self.invitation_id = None
            if not hasattr(self, 'expires_at'):
                self.expires_at = None

    monkeypatch.setattr("app.services.admin_service.invite_admin_service.Invitation", SimpleInvitation)
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.check_user_existence", AsyncMock(return_value=False))
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.send_admin_invite_email", AsyncMock(return_value=True))

    svc = InviteAdminService(db, cache)

    # integer days
    req = AdminInviteRequest(
        email="d1@example.com",
        first_name="D1",
        last_name="Test",
        phone_number=None,
        role="ADMIN",
        expiration_days=2
    )
    res = await svc.generate_admin_invite(req, invited_by_user_id=str(uuid.uuid4()))
    assert res.get("success") is True
    assert "2 days" in res.get("data").get("expires_in")

    # string that is integer
    req2 = AdminInviteRequest(
        email="d2@example.com",
        first_name="D2",
        last_name="Test",
        phone_number=None,
        role="ADMIN",
        expiration_days="1"
    )
    res2 = await svc.generate_admin_invite(req2, invited_by_user_id=str(uuid.uuid4()))
    assert res2.get("success") is True

    # zero -> fallback to default
    req3 = AdminInviteRequest(
        email="d3@example.com",
        first_name="D3",
        last_name="Test",
        phone_number=None,
        role="ADMIN",
        expiration_days=0
    )
    res3 = await svc.generate_admin_invite(req3, invited_by_user_id=str(uuid.uuid4()))
    assert res3.get("success") is True

    # non-int string -> pydantic should reject invalid int input
    with pytest.raises(Exception):
        AdminInviteRequest(
            email="d4@example.com",
            first_name="D4",
            last_name="Test",
            phone_number=None,
            role="ADMIN",
            expiration_days="abc"
        )


@pytest.mark.asyncio
async def test_complete_admin_setup_create_user_db_failure(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()
    invite_info = {
        "email": "failcreate@example.com",
        "mode_of_login": "admin_invite",
        "role": "ADMIN",
        "first_name": "Fail",
        "last_name": "Create"
    }
    cache.get = AsyncMock(return_value=json.dumps(invite_info))

    monkeypatch.setattr("app.services.admin_service.complete_admin_setup_service.check_user_existence", AsyncMock(return_value=False))
    # create_user_from_cache will raise
    monkeypatch.setattr("app.services.admin_service.complete_admin_setup_service.create_user_from_cache", AsyncMock(side_effect=Exception("db down")))

    svc = CompleteAdminSetupService(db, cache)

    with pytest.raises(HTTPException) as exc:
        await svc.complete_admin_setup("token-x", response=MagicMock())

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert cache.delete.called


@pytest.mark.asyncio
async def test_complete_admin_setup_notification_failure_is_nonfatal(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()
    invite_info = {
        "email": "notifyfail@example.com",
        "mode_of_login": "admin_invite",
        "role": "ADMIN",
        "first_name": "Notify",
        "last_name": "Fail"
    }
    cache.get = AsyncMock(return_value=json.dumps(invite_info))

    monkeypatch.setattr("app.services.admin_service.complete_admin_setup_service.check_user_existence", AsyncMock(return_value=False))

    class NewAdmin:
        def __init__(self):
            self.email = "notifyfail@example.com"
            self.first_name = "Notify"
            self.last_name = "Fail"
            self.user_id = str(uuid.uuid4())

    monkeypatch.setattr("app.services.admin_service.complete_admin_setup_service.create_user_from_cache", AsyncMock(return_value=NewAdmin()))
    # make _update_invitation_and_notify raise
    monkeypatch.setattr(CompleteAdminSetupService, "_update_invitation_and_notify", AsyncMock(side_effect=Exception("notify down")))

    svc = CompleteAdminSetupService(db, cache)
    res = await svc.complete_admin_setup("token-ok", response=MagicMock())
    assert res.get("success") is True
    assert cache.delete.called
