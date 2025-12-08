from fastapi.testclient import TestClient
import main
import app.api.v1.notification_routes as notif_mod
from app.db.connection_manager import get_db
from jose import jwt as jose_jwt
import app.db.redis_manager as redis_manager
import app.utils.authentication_utils as auth_utils
from starlette.responses import JSONResponse


def _stub_redis():
    class _DummyRedis:
        def get(self, *args, **kwargs):
            return None
        async def exists(self, *args, **kwargs):
            return False
    return _DummyRedis()


def test_get_notifications_and_unread_count_and_mark_delete(monkeypatch):
    client = TestClient(main.app)

    async def fake_get_notifications(request, db, unread_only, limit):
        return {"status_code": 200, "notifications": []}

    async def fake_get_unread_count(request, db):
        return {"status_code": 200, "unread": 3}

    async def fake_mark_read(request, db, notification_id):
        return {"status_code": 200, "marked": notification_id}

    async def fake_mark_all_read(request, db):
        return JSONResponse(content={"status_code": 202, "marked_all": True}, status_code=202)

    async def fake_delete(request, db, notification_id):
        return JSONResponse(content={"status_code": 204, "deleted": notification_id}, status_code=204)

    async def fake_get_db():
        yield None

    monkeypatch.setattr(notif_mod, "handle_get_notifications_controller", fake_get_notifications)
    monkeypatch.setattr(notif_mod, "handle_get_unread_count_controller", fake_get_unread_count)
    monkeypatch.setattr(notif_mod, "handle_mark_notification_read_controller", fake_mark_read)
    monkeypatch.setattr(notif_mod, "handle_mark_all_notifications_read_controller", fake_mark_all_read)
    monkeypatch.setattr(notif_mod, "handle_delete_notification_controller", fake_delete)

    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)
    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _stub_redis())
    # patch the middleware's imported is_jti_revoked to async False
    import app.authentication.jwt_middleware as jwt_mw
    async def _async_false(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", _async_false)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "u1", "jti": "n-jti-1", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    r = client.get("/api/v1/notifications/?unread_only=false&limit=10", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json().get("notifications") == []

    r2 = client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json().get("unread") == 3

    r3 = client.put("/api/v1/notifications/abcd-123/mark-read", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json().get("marked") == "abcd-123"

    r4 = client.put("/api/v1/notifications/mark-all-read", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 202
    assert r4.json().get("marked_all") is True

    r5 = client.delete("/api/v1/notifications/xyz-999", headers={"Authorization": f"Bearer {token}"})
    assert r5.status_code == 204
    assert r5.json().get("deleted") == "xyz-999"
from fastapi.testclient import TestClient
import main
import app.api.v1.notification_routes as notification_routes_mod
from app.db.connection_manager import get_db
from jose import jwt as jose_jwt
import app.db.redis_manager as redis_manager
import app.utils.authentication_utils as auth_utils


def _stub_redis():
    class _DummyRedis:
        def get(self, *args, **kwargs):
            return None

    return _DummyRedis()


def test_get_notifications_and_unread_count_and_mark_and_delete(monkeypatch):
    client = TestClient(main.app)

    async def fake_get_notifications(request, db, unread_only, limit):
        return {"notifications": [], "status_code": 200}

    async def fake_get_unread_count(request, db):
        return {"count": 0, "status_code": 200}

    async def fake_mark_read(request, db, notification_id):
        return {"notification_id": notification_id, "marked": True, "status_code": 200}

    async def fake_mark_all_read(request, db):
        return {"marked_all": True, "status_code": 200}

    async def fake_delete(request, db, notification_id):
        return {"deleted": notification_id, "status_code": 200}

    async def fake_get_db():
        yield None

    monkeypatch.setattr(notification_routes_mod, "handle_get_notifications_controller", fake_get_notifications)
    monkeypatch.setattr(notification_routes_mod, "handle_get_unread_count_controller", fake_get_unread_count)
    monkeypatch.setattr(notification_routes_mod, "handle_mark_notification_read_controller", fake_mark_read)
    monkeypatch.setattr(notification_routes_mod, "handle_mark_all_notifications_read_controller", fake_mark_all_read)
    monkeypatch.setattr(notification_routes_mod, "handle_delete_notification_controller", fake_delete)

    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)
    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _stub_redis())
    monkeypatch.setattr(auth_utils, "is_jti_revoked", lambda jti, r: False)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "test-user", "jti": "test-jti-5", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/v1/notifications/", headers=headers)
    assert r.status_code == 200
    assert r.json().get("notifications") == []

    r2 = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert r2.status_code == 200
    assert r2.json().get("count") == 0

    r3 = client.put("/api/v1/notifications/abcd-1/mark-read", headers=headers)
    assert r3.status_code == 200
    assert r3.json().get("marked") is True

    r4 = client.put("/api/v1/notifications/mark-all-read", headers=headers)
    assert r4.status_code == 200
    assert r4.json().get("marked_all") is True

    r5 = client.delete("/api/v1/notifications/abcd-2", headers=headers)
    assert r5.status_code == 200
    assert r5.json().get("deleted") == "abcd-2"
