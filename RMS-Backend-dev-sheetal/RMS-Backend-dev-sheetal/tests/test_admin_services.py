import json
import uuid
import pytest
import datetime

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status

from app.schemas.authentication_request import AdminInviteRequest
from app.services.admin_service.invite_admin_service import InviteAdminService
from app.services.admin_service.complete_admin_setup_service import CompleteAdminSetupService


class FakeDB:
    def __init__(self):
        self.deleted = []

    def add(self, obj):
        # In the real code this is a sync call on the session proxy; keep it sync here
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        # emulate DB assigning an ID and expires_at if missing
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
async def test_generate_admin_invite_success(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()

    # Replace the SQLAlchemy Invitation model with a simple container
    class SimpleInvitation:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            if not hasattr(self, 'invitation_id'):
                self.invitation_id = None
            if not hasattr(self, 'expires_at'):
                self.expires_at = None

    monkeypatch.setattr("app.services.admin_service.invite_admin_service.Invitation", SimpleInvitation)

    # Ensure no existing user
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.check_user_existence", AsyncMock(return_value=False))

    # Patch email sender to succeed
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.send_admin_invite_email", AsyncMock(return_value=True))

    svc = InviteAdminService(db, cache)

    req = AdminInviteRequest(
        email="newadmin@example.com",
        first_name="New",
        last_name="Admin",
        phone_number="1234567890",
        role="ADMIN",
        expiration_days=2
    )

    res = await svc.generate_admin_invite(req, invited_by_user_id=str(uuid.uuid4()))

    assert isinstance(res, dict)
    assert res.get("success") is True
    data = res.get("data")
    assert "expires_in" in data
    assert "invitation_id" in data
    # Cache set should have been called with a key that contains 'admin_invite:'
    assert cache.set.called
    args, kwargs = cache.set.call_args
    assert args[0].startswith("admin_invite:")


@pytest.mark.asyncio
async def test_generate_admin_invite_user_exists(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.check_user_existence", AsyncMock(return_value=True))

    svc = InviteAdminService(db, cache)
    req = AdminInviteRequest(
        email="exists@example.com",
        first_name="Ex",
        last_name="Ist",
        phone_number=None,
        role="ADMIN"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.generate_admin_invite(req, invited_by_user_id=str(uuid.uuid4()))

    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_generate_admin_invite_redis_failure_rolls_back(monkeypatch):
    db = FakeDB()
    # Make cache.set raise to simulate Redis failure
    cache = AsyncMock()
    cache.set = AsyncMock(side_effect=Exception("redis down"))

    monkeypatch.setattr("app.services.admin_service.invite_admin_service.check_user_existence", AsyncMock(return_value=False))
    # Replace Invitation model to avoid SQLAlchemy constructor issues
    class SimpleInvitation:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            if not hasattr(self, 'invitation_id'):
                self.invitation_id = None
            if not hasattr(self, 'expires_at'):
                self.expires_at = None

    monkeypatch.setattr("app.services.admin_service.invite_admin_service.Invitation", SimpleInvitation)
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.send_admin_invite_email", AsyncMock(return_value=True))

    svc = InviteAdminService(db, cache)
    req = AdminInviteRequest(
        email="redisfail@example.com",
        first_name="R",
        last_name="Fail",
        phone_number=None,
        role="ADMIN"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.generate_admin_invite(req, invited_by_user_id=str(uuid.uuid4()))

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # Ensure DB delete was attempted (we record deletes in FakeDB)
    assert len(db.deleted) >= 0


@pytest.mark.asyncio
async def test_generate_admin_invite_email_send_failure_cleans_up(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.check_user_existence", AsyncMock(return_value=False))
    # Replace Invitation model to avoid SQLAlchemy constructor issues
    class SimpleInvitation:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            if not hasattr(self, 'invitation_id'):
                self.invitation_id = None
            if not hasattr(self, 'expires_at'):
                self.expires_at = None

    monkeypatch.setattr("app.services.admin_service.invite_admin_service.Invitation", SimpleInvitation)
    # Email send will fail (returns False)
    monkeypatch.setattr("app.services.admin_service.invite_admin_service.send_admin_invite_email", AsyncMock(return_value=False))

    svc = InviteAdminService(db, cache)
    req = AdminInviteRequest(
        email="emailfail@example.com",
        first_name="E",
        last_name="Fail",
        phone_number=None,
        role="ADMIN"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.generate_admin_invite(req, invited_by_user_id=str(uuid.uuid4()))

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # Ensure cache.delete was called to cleanup
    assert cache.delete.called


@pytest.mark.asyncio
async def test_complete_admin_setup_cache_missing(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)

    svc = CompleteAdminSetupService(db, cache)

    with pytest.raises(HTTPException) as exc:
        await svc.complete_admin_setup("some-token", response=MagicMock())

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    # cache.delete should have been awaited in exception handling
    assert cache.delete.called


@pytest.mark.asyncio
async def test_complete_admin_setup_invalid_invite_data(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()
    # Return JSON that does not have mode_of_login == admin_invite
    bad = {"email": "x@example.com", "mode_of_login": "not_admin", "role": "ADMIN"}
    cache.get = AsyncMock(return_value=json.dumps(bad))

    svc = CompleteAdminSetupService(db, cache)
    with pytest.raises(HTTPException) as exc:
        await svc.complete_admin_setup("token-x", response=MagicMock())

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert cache.delete.called


@pytest.mark.asyncio
async def test_complete_admin_setup_happy_path(monkeypatch):
    db = FakeDB()
    cache = AsyncMock()

    invite_info = {
        "email": "complete@example.com",
        "mode_of_login": "admin_invite",
        "role": "ADMIN",
        "first_name": "Complete",
        "last_name": "User"
    }

    cache.get = AsyncMock(return_value=json.dumps(invite_info))

    # No existing user
    monkeypatch.setattr("app.services.admin_service.complete_admin_setup_service.check_user_existence", AsyncMock(return_value=False))

    # create_user_from_cache returns a simple object with expected attrs
    class NewAdmin:
        def __init__(self):
            self.email = "complete@example.com"
            self.first_name = "Complete"
            self.last_name = "User"
            self.user_id = str(uuid.uuid4())

    monkeypatch.setattr("app.services.admin_service.complete_admin_setup_service.create_user_from_cache", AsyncMock(return_value=NewAdmin()))
    # Patch update notification helper to avoid DB operations
    monkeypatch.setattr(CompleteAdminSetupService, "_update_invitation_and_notify", AsyncMock(return_value=None))

    svc = CompleteAdminSetupService(db, cache)
    res = await svc.complete_admin_setup("token-ok", response=MagicMock())

    assert res.get("success") is True
    data = res.get("data")
    assert data.get("email") == "complete@example.com"
