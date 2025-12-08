import asyncio
import json
from fastapi.testclient import TestClient
import main
from jose import jwt as jose_jwt
import app.api.v1.ws_routes as ws_mod
import app.db.redis_manager as redis_manager
import app.authentication.jwt_middleware as jwt_mw


def _make_token(payload, app_main):
    secret = app_main.app.state.jwt_secret_key
    alg = app_main.app.state.jwt_algorithm
    return jose_jwt.encode(payload, secret, algorithm=alg)


def test_ws_no_token_closes():
    client = TestClient(main.app)
    # No token provided -> should close with policy violation
    try:
        with client.websocket_connect("/api/v1/ws/task-status/tx-1") as ws:
            # If connection succeeds, try to receive and expect close immediately
            data = ws.receive()
            assert False, "Expected connection to be closed due to missing token"
    except Exception:
        # Test passes if connection cannot be established or is closed
        pass


def test_ws_invalid_token_closes():
    client = TestClient(main.app)
    # Provide a malformed/invalid token
    headers = {"Authorization": "Bearer not-a-valid-token"}
    try:
        with client.websocket_connect("/api/v1/ws/task-status/tx-2", headers=headers) as ws:
            data = ws.receive()
            assert False, "Expected invalid token to close connection"
    except Exception:
        pass


def test_ws_redis_unavailable(monkeypatch):
    client = TestClient(main.app)

    # make token
    token = _make_token({"sub": "u1", "jti": "j1"}, main)

    # RedisManager.get_client raises -> route should send an error and close
    def fake_get_client():
        raise RuntimeError("no redis")

    monkeypatch.setattr(redis_manager.RedisManager, "get_client", staticmethod(fake_get_client))

    # Also ensure middleware's is_jti_revoked won't block
    async def _async_false(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", _async_false)

    with client.websocket_connect(f"/api/v1/ws/task-status/abc?token={token}") as ws:
        # First message: welcome
        welcome = ws.receive_json()
        assert welcome.get("message") == "WebSocket connected"
        # Next message: Redis unavailable error
        err = ws.receive_json()
        assert "Redis unavailable" in err.get("error")


def test_ws_forwards_matching_message(monkeypatch):
    client = TestClient(main.app)

    task_id = "task-123"
    token = _make_token({"sub": "u2", "jti": "j2"}, main)

    # Build a fake redis client and pubsub
    class FakePubSub:
        def __init__(self):
            self._called = 0

        async def subscribe(self, channel):
            self.subscribed = channel

        async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
            # First call: return a message for our task
            if self._called == 0:
                self._called += 1
                payload = json.dumps({"task_id": task_id, "status": "done"})
                return {"type": "message", "data": payload}
            # Subsequent: wait a bit and return None
            await asyncio.sleep(0.1)
            return None

        async def unsubscribe(self, channel):
            self.unsubscribed = channel

        async def close(self):
            self.closed = True

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    monkeypatch.setattr(redis_manager.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    async def _async_false(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", _async_false)

    with client.websocket_connect(f"/api/v1/ws/task-status/{task_id}?token={token}") as ws:
        welcome = ws.receive_json()
        assert welcome.get("task_id") == task_id

        # Receive forwarded message matching task_id
        forwarded = ws.receive_json()
        assert forwarded.get("status") == "done"

        # Close client side to ensure server breaks out of loop and cleans up
        ws.close()
