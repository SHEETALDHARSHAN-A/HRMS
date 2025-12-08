import asyncio
import json
import types
import pytest

import app.api.v1.ws_routes as ws_mod
from app.api.v1 import ws_routes


def test_extract_token_cookies_raises_and_ignored():
    # Fake websocket where .cookies access raises Exception
    class BadCookies:
        def __getattr__(self, item):
            raise RuntimeError("cookies not available")

    class FakeWS:
        def __init__(self):
            self.query_params = {}
            self.headers = {}
            self.cookies = BadCookies()

    fake = FakeWS()
    # Should not raise, and should return None (no token)
    assert ws_mod._extract_token_from_websocket(fake) is None


@pytest.mark.asyncio
async def test_welcome_send_json_ignored_and_websocketdisconnect(monkeypatch):
    # Simulate welcome send_json raising, and pubsub raising WebSocketDisconnect
    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {"token": "tok"}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.accepted = False

        async def accept(self):
            self.accepted = True

        async def close(self, code=None):
            self.closed = True

        async def send_json(self, payload):
            # Simulate failure when sending welcome message
            raise RuntimeError("send failed")

    # Monkeypatch JWT decode to accept any token
    monkeypatch.setattr(ws_mod.jwt, "decode", lambda token, secret, algorithms: {"sub": "u1"})

    # Make pubsub that raises WebSocketDisconnect to hit that except
    class FakePubSub:
        async def subscribe(self, channel):
            self.sub = channel

        async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
            # Immediately raise WebSocketDisconnect to exit loop
            raise ws_mod.WebSocketDisconnect()

        async def unsubscribe(self, channel):
            self.unsub = channel

        async def close(self):
            self.closed = True

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    monkeypatch.setattr(ws_mod.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))

    fake_ws = FakeWS()
    # Should not raise despite send_json raising inside welcome
    await ws_mod.websocket_task_status(fake_ws, "task-x")


@pytest.mark.asyncio
async def test_payload_not_json_skipped_then_forward_and_unsubscribe_close_exceptions(monkeypatch):
    # This test covers: payload not JSON (skip), forwarding a matching message,
    # and final unsubscribe/close raising errors (should be ignored).

    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {"token": "tok"}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.sent = []

        async def accept(self):
            pass

        async def close(self, code=None):
            self.closed = True

        async def send_json(self, payload):
            # Record sent payloads
            self.sent.append(payload)

    # monkeypatch jwt.decode to return a payload with sub
    monkeypatch.setattr(ws_mod.jwt, "decode", lambda token, secret, algorithms: {"sub": "u2"})

    task_id = "T-1"

    class FakePubSub:
        def __init__(self):
            self._calls = 0

        async def subscribe(self, channel):
            self.sub = channel

        async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
            # First call: non-JSON payload
            if self._calls == 0:
                self._calls += 1
                return {"type": "message", "data": b"not-a-json"}
            # Second call: message for our task
            if self._calls == 1:
                self._calls += 1
                payload = json.dumps({"task_id": task_id, "status": "ok"})
                return {"type": "message", "data": payload}
            # Third call: after forwarding, raise to break and hit finally
            raise ws_mod.WebSocketDisconnect()

        async def unsubscribe(self, channel):
            # Simulate unsubscribe raising
            raise RuntimeError("unsubscribe failed")

        async def close(self):
            # Simulate close raising
            raise RuntimeError("close failed")

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    monkeypatch.setattr(ws_mod.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))

    fake_ws = FakeWS()
    await ws_mod.websocket_task_status(fake_ws, task_id)

    # Ensure we forwarded the matching message (welcome might be first)
    # The forwarded message should be present in sent list (status ok)
    assert any(isinstance(m, dict) and m.get("status") == "ok" for m in fake_ws.sent)


def test_extract_token_from_header():
    class FakeWS:
        def __init__(self):
            self.query_params = {}
            self.cookies = {}
            self.headers = {"authorization": "Bearer abc.def"}

    fake = FakeWS()
    assert ws_mod._extract_token_from_websocket(fake) == "abc.def"


@pytest.mark.asyncio
async def test_no_token_closes_direct():
    # Call the coroutine directly with a websocket that has no token
    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.closed_with = None

        async def close(self, code=None):
            self.closed_with = code

    fake = FakeWS()
    await ws_mod.websocket_task_status(fake, "t1")
    assert fake.closed_with == ws_mod.status.WS_1008_POLICY_VIOLATION


@pytest.mark.asyncio
async def test_jwt_decode_error_closes(monkeypatch):
    # Have token present but jwt.decode raises JWTError -> should close
    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {"token": "tok"}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.closed_with = None

        async def close(self, code=None):
            self.closed_with = code

    fake = FakeWS()
    monkeypatch.setattr(ws_mod.jwt, "decode", lambda *a, **k: (_ for _ in ()).throw(ws_mod.JWTError("bad")))
    await ws_mod.websocket_task_status(fake, "t2")
    assert fake.closed_with == ws_mod.status.WS_1008_POLICY_VIOLATION


@pytest.mark.asyncio
async def test_asyncio_sleep_exception_breaks(monkeypatch):
    # Ensure the inner try/except around asyncio.sleep handles exceptions
    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {"token": "tok"}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.sent = []

        async def accept(self):
            pass

        async def send_json(self, payload):
            self.sent.append(payload)

    # pubsub returns None messages so loop runs and then asyncio.sleep raises
    class FakePubSub:
        async def subscribe(self, channel):
            pass

        async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
            return None

        async def unsubscribe(self, channel):
            pass

        async def close(self):
            pass

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    monkeypatch.setattr(ws_mod.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    monkeypatch.setattr(ws_mod.jwt, "decode", lambda token, secret, algorithms: {"sub": "x"})

    async def fake_sleep(x):
        raise RuntimeError("boom")

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    fake = FakeWS()
    await ws_mod.websocket_task_status(fake, "task-sleep")


@pytest.mark.asyncio
async def test_forward_send_json_raises_break(monkeypatch):
    # Welcome succeeds, but forwarding the matching message raises -> break
    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {"token": "tok"}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.sent = []

        async def accept(self):
            pass

        async def send_json(self, payload):
            # First welcome call: allow, Second (forward) -> raise
            if not self.sent:
                self.sent.append(payload)
                return
            raise RuntimeError("client disconnected")

    class FakePubSub:
        def __init__(self):
            self._calls = 0

        async def subscribe(self, channel):
            pass

        async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
            if self._calls == 0:
                self._calls += 1
                return {"type": "message", "data": json.dumps({"task_id": "TF", "status": "go"})}
            # After sending matching message, raise to allow cleanup
            raise ws_mod.WebSocketDisconnect()

        async def unsubscribe(self, channel):
            pass

        async def close(self):
            pass

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    monkeypatch.setattr(ws_mod.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    monkeypatch.setattr(ws_mod.jwt, "decode", lambda token, secret, algorithms: {"sub": "y"})

    fake = FakeWS()
    # Should not raise even though send_json raises on forward
    await ws_mod.websocket_task_status(fake, "TF")


def test_extract_token_from_cookies():
    class FakeWS:
        def __init__(self):
            self.query_params = {}
            self.headers = {}
            self.cookies = {"access_token": "cookietok"}

    fake = FakeWS()
    assert ws_mod._extract_token_from_websocket(fake) == "cookietok"


@pytest.mark.asyncio
async def test_redis_get_client_exception_sends_error_and_closes(monkeypatch):
    # If RedisManager.get_client raises, the route should send an error and close
    class FakeAppState:
        jwt_secret_key = "secret"
        jwt_algorithm = "HS256"

    class FakeApp:
        state = FakeAppState()

    class FakeWS:
        def __init__(self):
            self.query_params = {"token": "tok"}
            self.headers = {}
            self.cookies = {}
            self.app = FakeApp()
            self.sent = []
            self.closed = False

        async def accept(self):
            pass

        async def send_json(self, payload):
            self.sent.append(payload)

        async def close(self, code=None):
            self.closed = True

    monkeypatch.setattr(ws_mod.jwt, "decode", lambda token, secret, algorithms: {"sub": "zzz"})
    monkeypatch.setattr(ws_mod.RedisManager, "get_client", staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no redis"))))

    fake = FakeWS()
    await ws_mod.websocket_task_status(fake, "task-redis")
    assert any("Redis unavailable" in (m.get("error") or "") for m in fake.sent)
    assert fake.closed
