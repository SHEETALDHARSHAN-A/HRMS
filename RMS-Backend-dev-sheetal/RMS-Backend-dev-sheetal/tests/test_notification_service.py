import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.notification.notification_service import NotificationService


@pytest.mark.asyncio
async def test_get_notifications_with_related_user(monkeypatch, fake_db):
    # prepare a notification with related_user_id
    notif = SimpleNamespace(notification_id='n1', type='INFO', title='T', message='M', is_read=False, created_at=None, read_at=None, related_invitation_id=None, related_user_id='u1')

    monkeypatch.setattr('app.services.notification.notification_service.fetch_notifications', AsyncMock(return_value=[notif]))
    related = SimpleNamespace(user_id='u1', first_name='F', last_name='L', email='e@example.com', role='CANDIDATE')
    monkeypatch.setattr('app.services.notification.notification_service.fetch_user_by_id', AsyncMock(return_value=related))

    svc = NotificationService(db=fake_db)
    res = await svc.get_notifications('u1')

    assert res['status_code'] == 200
    assert res['data']['notifications'][0]['related_user']['user_id'] == 'u1'


@pytest.mark.asyncio
async def test_get_notifications_handles_repo_exception(monkeypatch, fake_db):
    monkeypatch.setattr('app.services.notification.notification_service.fetch_notifications', AsyncMock(side_effect=Exception('db')))
    svc = NotificationService(db=fake_db)
    res = await svc.get_notifications('u1')
    assert res['success'] is False
    assert res['status_code'] == 500


@pytest.mark.asyncio
async def test_mark_notification_as_read_success_and_not_found(monkeypatch, fake_db):
    monkeypatch.setattr('app.services.notification.notification_service.mark_notification_read_db', AsyncMock(return_value=True))
    svc = NotificationService(db=fake_db)
    ok = await svc.mark_notification_as_read('n1', 'u1')
    assert ok['status_code'] == 200

    monkeypatch.setattr('app.services.notification.notification_service.mark_notification_read_db', AsyncMock(return_value=False))
    notfound = await svc.mark_notification_as_read('n2', 'u1')
    assert notfound['status_code'] == 404


@pytest.mark.asyncio
async def test_mark_all_notifications_and_get_unread_count(monkeypatch, fake_db):
    monkeypatch.setattr('app.services.notification.notification_service.mark_all_notifications_read_db', AsyncMock(return_value=5))
    monkeypatch.setattr('app.services.notification.notification_service.get_unread_count_db', AsyncMock(return_value=2))
    svc = NotificationService(db=fake_db)
    res = await svc.mark_all_notifications_as_read('u1')
    assert res['status_code'] == 200
    assert res['data']['updated_count'] == 5

    res2 = await svc.get_unread_count('u1')
    assert res2['status_code'] == 200
    assert res2['data']['unread_count'] == 2


@pytest.mark.asyncio
async def test_delete_notification_success_and_not_found(monkeypatch, fake_db):
    monkeypatch.setattr('app.services.notification.notification_service.delete_notification_db', AsyncMock(return_value=True))
    svc = NotificationService(db=fake_db)
    res = await svc.delete_notification('n1', 'u1')
    assert res['status_code'] == 200

    monkeypatch.setattr('app.services.notification.notification_service.delete_notification_db', AsyncMock(return_value=False))
    res2 = await svc.delete_notification('n2', 'u1')
    assert res2['status_code'] == 404
