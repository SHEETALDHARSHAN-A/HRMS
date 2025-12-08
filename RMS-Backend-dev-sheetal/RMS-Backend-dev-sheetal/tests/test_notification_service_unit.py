import pytest
from types import SimpleNamespace

import app.services.notification.notification_service as svc_mod
from app.services.notification.notification_service import NotificationService


class DummyNotification:
    def __init__(self, nid, type_, title, message, is_read=False, created_at=None, read_at=None, related_invitation_id=None, related_user_id=None):
        self.notification_id = nid
        self.type = type_
        self.title = title
        self.message = message
        self.is_read = is_read
        self.created_at = created_at
        self.read_at = read_at
        self.related_invitation_id = related_invitation_id
        self.related_user_id = related_user_id


class DummyUser:
    def __init__(self, uid, first_name, last_name, email, role):
        self.user_id = uid
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.role = role


@pytest.mark.asyncio
async def test_get_notifications_includes_related_user(monkeypatch):
    dummy = DummyNotification('n1', 'info', 'T', 'M', related_user_id='u1')

    async def fake_fetch_notifications(db, user_id, unread_only, limit):
        return [dummy]

    async def fake_fetch_user_by_id(db, user_id):
        return DummyUser('u1', 'First', 'Last', 'a@example.com', 'ADMIN')

    monkeypatch.setattr(svc_mod, 'fetch_notifications', fake_fetch_notifications)
    monkeypatch.setattr(svc_mod, 'fetch_user_by_id', fake_fetch_user_by_id)

    service = NotificationService(db='DB')
    res = await service.get_notifications('user-x', False, 10)
    assert res['status_code'] == 200
    assert res['data']['notifications'][0]['related_user']['email'] == 'a@example.com'


@pytest.mark.asyncio
async def test_mark_notification_as_read_not_found(monkeypatch):
    async def fake_mark(db, nid, uid):
        return False

    monkeypatch.setattr(svc_mod, 'mark_notification_read_db', fake_mark)
    service = NotificationService(db='DB')
    res = await service.mark_notification_as_read('nid', 'user')
    assert res['status_code'] == 404


@pytest.mark.asyncio
async def test_mark_notification_as_read_success(monkeypatch):
    async def fake_mark(db, nid, uid):
        return True

    monkeypatch.setattr(svc_mod, 'mark_notification_read_db', fake_mark)
    service = NotificationService(db='DB')
    res = await service.mark_notification_as_read('nid', 'user')
    assert res['status_code'] == 200
    assert res['data']['notification_id'] == 'nid'


@pytest.mark.asyncio
async def test_mark_all_and_unread_and_delete(monkeypatch):
    async def fake_mark_all(db, uid):
        return 3

    async def fake_unread(db, uid):
        return 7

    async def fake_delete(db, nid, uid):
        return True

    monkeypatch.setattr(svc_mod, 'mark_all_notifications_read_db', fake_mark_all)
    monkeypatch.setattr(svc_mod, 'get_unread_count_db', fake_unread)
    monkeypatch.setattr(svc_mod, 'delete_notification_db', fake_delete)

    service = NotificationService(db='DB')
    r1 = await service.mark_all_notifications_as_read('u')
    assert r1['status_code'] == 200
    assert r1['data']['updated_count'] == 3

    r2 = await service.get_unread_count('u')
    assert r2['status_code'] == 200
    assert r2['data']['unread_count'] == 7

    r3 = await service.delete_notification('nid', 'u')
    assert r3['status_code'] == 200
