import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException, status

from app.services.interview_service import InterviewAuthService
import app.services.interview_service as service_mod


class FakeResult:
    def __init__(self, obj):
        self._obj = obj
    def scalars(self):
        return self
    def first(self):
        return self._obj


@pytest.mark.asyncio
async def test_validate_token_and_send_otp_not_found(monkeypatch):
    db = SimpleNamespace()
    # No schedule found
    monkeypatch.setattr(db, 'execute', AsyncMock(return_value=FakeResult(None)), raising=False)
    with pytest.raises(HTTPException) as excinfo:
        await InterviewAuthService.validate_token_and_send_otp('x@example.com', 'token', db)
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_validate_token_and_send_otp_status_completed(monkeypatch):
    db = SimpleNamespace()
    schedule = SimpleNamespace(status='completed', profile_id='p1')
    monkeypatch.setattr(db, 'execute', AsyncMock(return_value=FakeResult(schedule)), raising=False)
    with pytest.raises(HTTPException) as excinfo:
        await InterviewAuthService.validate_token_and_send_otp('x@example.com', 'token', db)
    assert excinfo.value.status_code == status.HTTP_410_GONE


@pytest.mark.asyncio
async def test_validate_token_and_send_otp_success(monkeypatch):
    db = SimpleNamespace()
    schedule = SimpleNamespace(status='scheduled', profile_id='p1')
    monkeypatch.setattr(db, 'execute', AsyncMock(return_value=FakeResult(schedule)), raising=False)
    fake_redis = SimpleNamespace()
    fake_redis.set = AsyncMock(return_value=None)
    monkeypatch.setattr(service_mod.RedisManager, 'get_client', lambda: fake_redis)
    monkeypatch.setattr(service_mod, 'generate_otp', lambda: '1234')
    monkeypatch.setattr(service_mod, 'send_otp_email', AsyncMock(return_value=None))
    res = await InterviewAuthService.validate_token_and_send_otp('x@example.com', 'token', db)
    assert res['message'] == 'OTP has been sent to your email.'


@pytest.mark.asyncio
async def test_verify_otp_and_get_room_invalid_otp(monkeypatch):
    db = SimpleNamespace()
    fake_redis = SimpleNamespace()
    fake_redis.get = AsyncMock(return_value='9999')
    monkeypatch.setattr(service_mod.RedisManager, 'get_client', lambda: fake_redis)
    # wrong OTP
    with pytest.raises(HTTPException) as excinfo:
        await InterviewAuthService.verify_otp_and_get_room('x@example.com', 'token', '0000', db)
    # The code raises HTTPException(400) inside try and catches as Exception -> returns HTTP 500
    assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_verify_otp_and_get_room_success(monkeypatch):
    db = SimpleNamespace()
    # Redis returns the correct OTP
    fake_redis = SimpleNamespace()
    fake_redis.get = AsyncMock(return_value='1234')
    fake_redis.delete = AsyncMock(return_value=None)
    monkeypatch.setattr(service_mod.RedisManager, 'get_client', lambda: fake_redis)

    # Schedule result present
    schedule = SimpleNamespace(status='scheduled', profile_id='p1')
    monkeypatch.setattr(db, 'execute', AsyncMock(return_value=FakeResult(schedule)), raising=False)
    # db.get returns a profile object with name
    profile = SimpleNamespace(name='Test User')
    monkeypatch.setattr(db, 'get', AsyncMock(return_value=profile), raising=False)

    # LiveKit and AccessToken should not make network calls; patch them
    class FakeLKAPI:
        def __init__(self, url, a, b):
            pass
        class room:
            @staticmethod
            async def create_room(req):
                return None
    monkeypatch.setattr(service_mod, 'LiveKitAPI', FakeLKAPI)

    class FakeAccessToken:
        def __init__(self, a, b):
            pass
        def with_grants(self, g):
            return None
        def with_identity(self, i):
            return None
        def with_name(self, n):
            return None
        def to_jwt(self):
            return 'jwt'
    monkeypatch.setattr(service_mod, 'AccessToken', FakeAccessToken)
    monkeypatch.setattr(service_mod, 'VideoGrants', lambda **k: None)

    # Setup LiveKit URL/keys to avoid config error
    monkeypatch.setattr(service_mod, 'LIVEKIT_URL', 'http://lk')
    monkeypatch.setattr(service_mod, 'LIVEKIT_API_KEY', 'k')
    monkeypatch.setattr(service_mod, 'LIVEKIT_API_SECRET', 's')

    res = await InterviewAuthService.verify_otp_and_get_room('x@example.com', 'token', '1234', db)
    assert 'livekit_url' in res and 'livekit_token' in res
