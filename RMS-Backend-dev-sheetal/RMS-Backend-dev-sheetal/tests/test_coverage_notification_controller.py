import pytest
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request

from app.controllers.notification_controller import (
    handle_get_notifications_controller,
    handle_mark_notification_read_controller,
    handle_mark_all_notifications_read_controller,
    handle_get_unread_count_controller,
    handle_delete_notification_controller,
)


@pytest.mark.asyncio
async def test_get_notifications_requires_auth():
    res = await handle_get_notifications_controller(MagicMock(state=SimpleNamespace()), AsyncMock(), unread_only=False, limit=10)
    # MagicMock.state has no user -> authentication required
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_notifications_success():
    req = MagicMock()
    req.state.user = {"sub": "u1"}

    class FakeService:
        def __init__(self, db):
            pass

        async def get_notifications(self, user_id, unread_only, limit):
            return {"status_code": 200, "notifications": [1,2,3]}

    with patch('app.controllers.notification_controller.NotificationService', FakeService):
        res = await handle_get_notifications_controller(req, AsyncMock(), unread_only=True, limit=5)
        assert res.status_code == 200
        body = json.loads(res.body)
        assert 'notifications' in body


@pytest.mark.asyncio
async def test_mark_notification_read_requires_auth():
    res = await handle_mark_notification_read_controller(MagicMock(state=SimpleNamespace()), AsyncMock(), 'n1')
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_mark_notification_read_success():
    req = MagicMock()
    req.state.user = {"user_id": "u1"}

    class FakeService:
        def __init__(self, db): pass
        async def mark_notification_as_read(self, nid, uid):
            return {"status_code": 200, "success": True}

    with patch('app.controllers.notification_controller.NotificationService', FakeService):
        res = await handle_mark_notification_read_controller(req, AsyncMock(), 'n1')
        assert res.status_code == 200
        body = json.loads(res.body)
        assert body.get('success') is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read_success_and_requires_auth():
    # No auth
    res = await handle_mark_all_notifications_read_controller(MagicMock(state=SimpleNamespace()), AsyncMock())
    assert res.status_code == 401

    # With auth
    req = MagicMock()
    req.state.user = {"sub": "u1"}

    class FakeService2:
        def __init__(self, db): pass
        async def mark_all_notifications_as_read(self, uid):
            return {"status_code": 200, "updated": 5}

    with patch('app.controllers.notification_controller.NotificationService', FakeService2):
        res2 = await handle_mark_all_notifications_read_controller(req, AsyncMock())
        assert res2.status_code == 200
        body = json.loads(res2.body)
        assert body.get('updated') == 5


@pytest.mark.asyncio
async def test_get_unread_count_and_delete_requires_auth():
    # unread count no auth
    res = await handle_get_unread_count_controller(MagicMock(state=SimpleNamespace()), AsyncMock())
    assert res.status_code == 401

    # delete no auth
    res2 = await handle_delete_notification_controller(MagicMock(state=SimpleNamespace()), AsyncMock(), 'n1')
    assert res2.status_code == 401

    # with auth
    req = MagicMock()
    req.state.user = {"user_id": "u1"}

    class FakeService3:
        def __init__(self, db): pass
        async def get_unread_count(self, uid):
            return {"status_code": 200, "count": 3}
        async def delete_notification(self, nid, uid):
            return {"status_code": 200, "deleted": True}

    with patch('app.controllers.notification_controller.NotificationService', FakeService3):
        rcount = await handle_get_unread_count_controller(req, AsyncMock())
        assert rcount.status_code == 200
        bodyc = json.loads(rcount.body)
        assert bodyc.get('count') == 3

        rdel = await handle_delete_notification_controller(req, AsyncMock(), 'n1')
        assert rdel.status_code == 200
        bodyd = json.loads(rdel.body)
        assert bodyd.get('deleted') is True


@pytest.mark.asyncio
async def test_get_notifications_exception_handling():
    """Test exception handling in handle_get_notifications_controller - covers lines 42-46"""
    req = MagicMock()
    req.state.user = {"user_id": "u1"}

    class FakeServiceRaise:
        def __init__(self, db): pass
        async def get_notifications(self, user_id, unread_only, limit):
            raise ValueError("Database error")

    with patch('app.controllers.notification_controller.NotificationService', FakeServiceRaise):
        res = await handle_get_notifications_controller(req, AsyncMock(), unread_only=False, limit=10)
        assert res.status_code == 500
        body = json.loads(res.body)
        assert 'Internal server error' in body['message']


@pytest.mark.asyncio
async def test_mark_notification_read_exception_handling():
    """Test exception handling in handle_mark_notification_read_controller - covers lines 75-79"""
    req = MagicMock()
    req.state.user = {"user_id": "u1"}

    class FakeServiceRaise:
        def __init__(self, db): pass
        async def mark_notification_as_read(self, nid, uid):
            raise RuntimeError("Update failed")

    with patch('app.controllers.notification_controller.NotificationService', FakeServiceRaise):
        res = await handle_mark_notification_read_controller(req, AsyncMock(), 'n1')
        assert res.status_code == 500
        body = json.loads(res.body)
        assert 'Internal server error' in body['message']


@pytest.mark.asyncio
async def test_mark_all_notifications_read_exception_handling():
    """Test exception handling in handle_mark_all_notifications_read_controller - covers lines 108-112"""
    req = MagicMock()
    req.state.user = {"sub": "u1"}

    class FakeServiceRaise:
        def __init__(self, db): pass
        async def mark_all_notifications_as_read(self, uid):
            raise ConnectionError("Database connection lost")

    with patch('app.controllers.notification_controller.NotificationService', FakeServiceRaise):
        res = await handle_mark_all_notifications_read_controller(req, AsyncMock())
        assert res.status_code == 500
        body = json.loads(res.body)
        assert 'Internal server error' in body['message']


@pytest.mark.asyncio
async def test_get_unread_count_exception_handling():
    """Test exception handling in handle_get_unread_count_controller - covers lines 141-145"""
    req = MagicMock()
    req.state.user = {"user_id": "u1"}

    class FakeServiceRaise:
        def __init__(self, db): pass
        async def get_unread_count(self, uid):
            raise Exception("Count query failed")

    with patch('app.controllers.notification_controller.NotificationService', FakeServiceRaise):
        res = await handle_get_unread_count_controller(req, AsyncMock())
        assert res.status_code == 500
        body = json.loads(res.body)
        assert 'Internal server error' in body['message']


@pytest.mark.asyncio
async def test_delete_notification_exception_handling():
    """Test exception handling in handle_delete_notification_controller - covers lines 174-178"""
    req = MagicMock()
    req.state.user = {"sub": "u1"}

    class FakeServiceRaise:
        def __init__(self, db): pass
        async def delete_notification(self, nid, uid):
            raise PermissionError("Cannot delete notification")

    with patch('app.controllers.notification_controller.NotificationService', FakeServiceRaise):
        res = await handle_delete_notification_controller(req, AsyncMock(), 'n1')
        assert res.status_code == 500
        body = json.loads(res.body)
        assert 'Internal server error' in body['message']


@pytest.mark.asyncio
async def test_get_notifications_missing_user_id():
    """Test get_notifications when user_id is not in token - covers line 29"""
    req = MagicMock()
    req.state.user = {"email": "test@test.com"}  # Valid user but no user_id or sub

    res = await handle_get_notifications_controller(req, AsyncMock(), unread_only=False, limit=10)
    assert res.status_code == 401
    body = json.loads(res.body)
    assert 'User ID not found' in body['message']


@pytest.mark.asyncio
async def test_mark_notification_read_missing_user_id():
    """Test mark_notification_read when user_id is not in token - covers line 62"""
    req = MagicMock()
    req.state.user = {"email": "test@test.com"}  # Valid user but no user_id

    res = await handle_mark_notification_read_controller(req, AsyncMock(), 'n1')
    assert res.status_code == 401
    body = json.loads(res.body)
    assert 'User ID not found' in body['message']


@pytest.mark.asyncio
async def test_mark_all_notifications_read_missing_user_id():
    """Test mark_all_notifications_read when user_id is not in token - covers line 95"""
    req = MagicMock()
    req.state.user = {"email": "test@test.com"}  # Valid user but no user_id

    res = await handle_mark_all_notifications_read_controller(req, AsyncMock())
    assert res.status_code == 401
    body = json.loads(res.body)
    assert 'User ID not found' in body['message']


@pytest.mark.asyncio
async def test_get_unread_count_missing_user_id():
    """Test get_unread_count when user_id is not in token - covers line 128"""
    req = MagicMock()
    req.state.user = {"email": "test@test.com"}  # Valid user but no user_id

    res = await handle_get_unread_count_controller(req, AsyncMock())
    assert res.status_code == 401
    body = json.loads(res.body)
    assert 'User ID not found' in body['message']


@pytest.mark.asyncio
async def test_delete_notification_missing_user_id():
    """Test delete_notification when user_id is not in token - covers line 161"""
    req = MagicMock()
    req.state.user = {"email": "test@test.com"}  # Valid user but no user_id

    res = await handle_delete_notification_controller(req, AsyncMock(), 'n1')
    assert res.status_code == 401
    body = json.loads(res.body)
    assert 'User ID not found' in body['message']


