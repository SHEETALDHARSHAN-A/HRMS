import pytest
from types import SimpleNamespace

import app.controllers.notification_controller as controller


class DummyService:
    def __init__(self, db):
        self.db = db

    async def get_notifications(self, user_id, unread_only, limit):
        return {"status_code": 200, "data": [{"id": "n1"}], "meta": {"limit": limit}}

    async def mark_notification_as_read(self, notification_id, user_id):
        return {"status_code": 200, "message": "marked", "id": notification_id}

    async def mark_all_notifications_as_read(self, user_id):
        return {"status_code": 200, "message": "all_marked"}

    async def get_unread_count(self, user_id):
        return {"status_code": 200, "count": 5}

    async def delete_notification(self, notification_id, user_id):
        return {"status_code": 200, "message": "deleted", "id": notification_id}


@pytest.mark.asyncio
async def test_get_notifications_unauthenticated():
    req = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await controller.handle_get_notifications_controller(req, db=None)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_notifications_authenticated(monkeypatch):
    # Patch the NotificationService used in the controller
    monkeypatch.setattr(controller, "NotificationService", DummyService)
    req = SimpleNamespace(state=SimpleNamespace(user={"user_id": "user-1"}))
    resp = await controller.handle_get_notifications_controller(req, db="FAKE_DB", unread_only=False, limit=10)
    assert resp.status_code == 200
    import json
    body = json.loads(resp.body)
    assert body["data"][0]["id"] == "n1"
    assert body["meta"]["limit"] == 10


@pytest.mark.asyncio
async def test_mark_notification_read(monkeypatch):
    monkeypatch.setattr(controller, "NotificationService", DummyService)
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-2"}))
    resp = await controller.handle_mark_notification_read_controller(req, db="DB", notification_id="notif-1")
    assert resp.status_code == 200
    import json
    body = json.loads(resp.body)
    assert body["id"] == "notif-1"


@pytest.mark.asyncio
async def test_mark_all_notifications_read(monkeypatch):
    monkeypatch.setattr(controller, "NotificationService", DummyService)
    req = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u3"}))
    resp = await controller.handle_mark_all_notifications_read_controller(req, db="DB")
    assert resp.status_code == 200
    import json
    body = json.loads(resp.body)
    assert body["message"] == "all_marked"


@pytest.mark.asyncio
async def test_get_unread_count(monkeypatch):
    monkeypatch.setattr(controller, "NotificationService", DummyService)
    req = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u3"}))
    resp = await controller.handle_get_unread_count_controller(req, db="DB")
    assert resp.status_code == 200
    import json
    body = json.loads(resp.body)
    assert body["count"] == 5


@pytest.mark.asyncio
async def test_delete_notification(monkeypatch):
    monkeypatch.setattr(controller, "NotificationService", DummyService)
    req = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u3"}))
    resp = await controller.handle_delete_notification_controller(req, db="DB", notification_id="nid-9")
    assert resp.status_code == 200
    import json
    body = json.loads(resp.body)
    assert body["id"] == "nid-9"
