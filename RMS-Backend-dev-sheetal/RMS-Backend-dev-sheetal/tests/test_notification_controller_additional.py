import pytest
from types import SimpleNamespace
from fastapi import status

from app.controllers import notification_controller as nc


# Minimal fake DB
fake_db = object()


@pytest.mark.asyncio
async def test_handle_get_notifications_controller_unauth(monkeypatch):
    # No user in state -> unauthorized
    request = SimpleNamespace(state=SimpleNamespace(user=None))
    res = await nc.handle_get_notifications_controller(request, fake_db)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_handle_get_notifications_controller_no_state(monkeypatch):
    # No state attr on request -> this currently raises and returns 500
    request = SimpleNamespace()
    res = await nc.handle_get_notifications_controller(request, fake_db)
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_handle_get_notifications_controller_no_user_id(monkeypatch):
    request = SimpleNamespace(state=SimpleNamespace(user={}))
    res = await nc.handle_get_notifications_controller(request, fake_db)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_handle_get_notifications_controller_service_error(monkeypatch):
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def get_notifications(self, user_id, unread_only, limit):
            raise RuntimeError("boom")

    monkeypatch.setattr(nc, "NotificationService", FakeService)
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"}))
    res = await nc.handle_get_notifications_controller(request, fake_db)
    assert res.status_code == 500

    # Use 'sub' as user identifier (instead of user_id) to hit the secondary path
    class FakeServiceSub:
        def __init__(self, db):
            self.db = db
        async def get_notifications(self, user_id, unread_only, limit):
            return {"status_code": 200, "data": {"notifications": []}}

    monkeypatch.setattr(nc, "NotificationService", FakeServiceSub)
    request_sub = SimpleNamespace(state=SimpleNamespace(user={"sub": "u-1"}))
    res_sub = await nc.handle_get_notifications_controller(request_sub, fake_db)
    assert res_sub.status_code == 200


@pytest.mark.asyncio
async def test_handle_get_notifications_controller_success(monkeypatch):
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def get_notifications(self, user_id, unread_only, limit):
            return {"status_code": 200, "data": {"notifications": []}}

    monkeypatch.setattr(nc, "NotificationService", FakeService)
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"}))
    res = await nc.handle_get_notifications_controller(request, fake_db)
    assert res.status_code == 200


# MARK AS READ
@pytest.mark.asyncio
async def test_handle_mark_notification_read_controller_auth_and_service(monkeypatch):
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def mark_notification_as_read(self, notification_id, user_id):
            if notification_id == "notfound":
                return {"status_code": 404}
            return {"status_code": 200, "data": {"notification_id": notification_id}}

    monkeypatch.setattr(nc, "NotificationService", FakeService)

    # Unauthorized
    request_none = SimpleNamespace(state=SimpleNamespace(user=None))
    res_none = await nc.handle_mark_notification_read_controller(request_none, fake_db, "x")
    assert res_none.status_code == 401

    # No user_id
    request_no_uid = SimpleNamespace(state=SimpleNamespace(user={}))
    res_no_uid = await nc.handle_mark_notification_read_controller(request_no_uid, fake_db, "x")
    assert res_no_uid.status_code == 401

    # Found
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"}))
    res_ok = await nc.handle_mark_notification_read_controller(request, fake_db, "1")
    assert res_ok.status_code == 200

    # Not found
    res_nf = await nc.handle_mark_notification_read_controller(request, fake_db, "notfound")
    assert res_nf.status_code == 404

    # Service exception -> 500
    class FakeServiceRaise:
        def __init__(self, db):
            self.db = db

        async def mark_notification_as_read(self, notification_id, user_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(nc, "NotificationService", FakeServiceRaise)
    res_exc = await nc.handle_mark_notification_read_controller(request, fake_db, "1")
    assert res_exc.status_code == 500

    # Missing state on request -> AttributeError -> 500
    res_state_missing = await nc.handle_mark_notification_read_controller(SimpleNamespace(), fake_db, "1")
    assert res_state_missing.status_code == 500

    # Also test using 'sub' as the id
    monkeypatch.setattr(nc, "NotificationService", FakeService)
    request_sub = SimpleNamespace(state=SimpleNamespace(user={"sub": "u-1"}))
    res_sub = await nc.handle_mark_notification_read_controller(request_sub, fake_db, "1")
    assert res_sub.status_code == 200


@pytest.mark.asyncio
async def test_handle_mark_all_notifications_read_controller(monkeypatch):
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def mark_all_notifications_as_read(self, user_id):
            return {"status_code": 200, "data": {"updated_count": 3}}

    monkeypatch.setattr(nc, "NotificationService", FakeService)

    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"}))
    res = await nc.handle_mark_all_notifications_read_controller(request, fake_db)
    assert res.status_code == 200
    # No user id in token -> 401
    request_no_uid = SimpleNamespace(state=SimpleNamespace(user={}))
    res_no_uid = await nc.handle_mark_all_notifications_read_controller(request_no_uid, fake_db)
    assert res_no_uid.status_code == 401

    # Also test 'sub' key present
    class FakeServiceSubAll:
        def __init__(self, db):
            self.db = db
        async def mark_all_notifications_as_read(self, user_id):
            return {"status_code": 200}

    monkeypatch.setattr(nc, "NotificationService", FakeServiceSubAll)
    res_sub = await nc.handle_mark_all_notifications_read_controller(SimpleNamespace(state=SimpleNamespace(user={"sub": "u-1"})), fake_db)
    assert res_sub.status_code == 200

    # Service raises -> 500
    class FakeServiceRaiseAll:
        def __init__(self, db):
            self.db = db

        async def mark_all_notifications_as_read(self, user_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(nc, "NotificationService", FakeServiceRaiseAll)
    res_exc = await nc.handle_mark_all_notifications_read_controller(request, fake_db)
    assert res_exc.status_code == 500

    # Missing state -> 500
    res_state_missing = await nc.handle_mark_all_notifications_read_controller(SimpleNamespace(), fake_db)
    assert res_state_missing.status_code == 500


@pytest.mark.asyncio
async def test_handle_get_unread_count_controller(monkeypatch):
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def get_unread_count(self, user_id):
            return {"status_code": 200, "data": {"unread_count": 5}}

    monkeypatch.setattr(nc, "NotificationService", FakeService)
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"}))
    res = await nc.handle_get_unread_count_controller(request, fake_db)
    assert res.status_code == 200
    request_no_uid = SimpleNamespace(state=SimpleNamespace(user={}))
    res_no_uid = await nc.handle_get_unread_count_controller(request_no_uid, fake_db)
    assert res_no_uid.status_code == 401

    # 'sub' key present
    class FakeServiceSubCount:
        def __init__(self, db):
            self.db = db
        async def get_unread_count(self, user_id):
            return {"status_code": 200, "data": {"unread_count": 1}}

    monkeypatch.setattr(nc, "NotificationService", FakeServiceSubCount)
    res_sub = await nc.handle_get_unread_count_controller(SimpleNamespace(state=SimpleNamespace(user={"sub": "u-1"})), fake_db)
    assert res_sub.status_code == 200

    # Service raises -> 500
    class FakeServiceRaiseCount:
        def __init__(self, db):
            self.db = db

        async def get_unread_count(self, user_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(nc, "NotificationService", FakeServiceRaiseCount)
    res_exc = await nc.handle_get_unread_count_controller(request, fake_db)
    assert res_exc.status_code == 500

    # Missing state -> 500
    res_state_missing = await nc.handle_get_unread_count_controller(SimpleNamespace(), fake_db)
    assert res_state_missing.status_code == 500


@pytest.mark.asyncio
async def test_handle_delete_notification_controller(monkeypatch):
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def delete_notification(self, notification_id, user_id):
            if notification_id == "notfound":
                return {"status_code": 404}
            return {"status_code": 200, "data": {"notification_id": notification_id}}

    monkeypatch.setattr(nc, "NotificationService", FakeService)

    # No auth
    res_no = await nc.handle_delete_notification_controller(SimpleNamespace(state=SimpleNamespace(user=None)), fake_db, "1")
    assert res_no.status_code == 401

    # No user id
    res_no_uid = await nc.handle_delete_notification_controller(SimpleNamespace(state=SimpleNamespace(user={})), fake_db, "1")
    assert res_no_uid.status_code == 401

    # Found
    res_ok = await nc.handle_delete_notification_controller(SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"})), fake_db, "1")
    assert res_ok.status_code == 200

    # Not found
    res_nf = await nc.handle_delete_notification_controller(SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"})), fake_db, "notfound")
    assert res_nf.status_code == 404

    # Service raise -> 500
    class FakeServiceRaiseDelete:
        def __init__(self, db):
            self.db = db

        async def delete_notification(self, notification_id, user_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(nc, "NotificationService", FakeServiceRaiseDelete)
    res_exc = await nc.handle_delete_notification_controller(SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"})), fake_db, "1")
    assert res_exc.status_code == 500

    # Missing state -> 500
    res_state_missing = await nc.handle_delete_notification_controller(SimpleNamespace(), fake_db, "1")
    assert res_state_missing.status_code == 500

    # 'sub' as user id
    monkeypatch.setattr(nc, "NotificationService", FakeService)
    res_sub = await nc.handle_delete_notification_controller(SimpleNamespace(state=SimpleNamespace(user={"sub": "u-1"})), fake_db, "1")
    assert res_sub.status_code == 200
