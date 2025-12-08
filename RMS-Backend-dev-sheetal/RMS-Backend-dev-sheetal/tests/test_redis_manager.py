import json
import pytest

from app.db import redis_manager


@pytest.mark.asyncio
async def test_safe_set_with_none_client_returns_false():
    res = await redis_manager.safe_set(None, "key", "val")
    assert res is False


@pytest.mark.asyncio
async def test_publish_activation_event_with_none_client_returns_false():
    res = await redis_manager.publish_activation_event(None, job_id="j1")
    assert res is False


@pytest.mark.asyncio
async def test_safe_set_retries_then_succeeds():
    class DummyClient:
        def __init__(self):
            self.calls = 0

        async def set(self, key, value, ex=None, nx=False):
            self.calls += 1
            if self.calls < 2:
                raise ConnectionError("transient")
            return True

    client = DummyClient()
    res = await redis_manager.safe_set(client, "k", "v", ex=1, retries=3)
    assert res is True
    assert client.calls == 2


@pytest.mark.asyncio
async def test_publish_activation_event_pushes_json():
    pushed = []

    class DummyClient2:
        async def rpush(self, key, value):
            pushed.append((key, value))
            return 1

    client = DummyClient2()
    ok = await redis_manager.publish_activation_event(client, job_id="job-x", profile_id="profile-y")
    assert ok is True
    assert len(pushed) == 1
    key, payload = pushed[0]
    assert key == redis_manager.ACTIVATION_QUEUE_KEY
    obj = json.loads(payload)
    assert obj["job_id"] == "job-x"
    assert obj["profile_id"] == "profile-y"
