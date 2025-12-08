import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.schemas.authentication_request import SendOTPRequest

from app.services.authentication_service.send_otp_service import SendOtpService
from app.services.authentication_service.resend_otp_service import ResendOtpService


@pytest.mark.asyncio
async def test_send_otp_user_not_registered_raises(monkeypatch, fake_db, fake_cache):
    # mock check_user_existence to return None
    # patch the symbol that the service module actually calls
    monkeypatch.setattr(
        'app.services.authentication_service.send_otp_service.check_user_existence',
        AsyncMock(return_value=None)
    )

    svc = SendOtpService(db=fake_db, cache=fake_cache)

    req = SendOTPRequest(email='user@example.com')

    with pytest.raises(HTTPException) as exc:
        await svc.send_otp(req)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_send_otp_success_sets_redis_and_sends_email(monkeypatch, fake_db, fake_cache):
    # create fake user
    fake_user = SimpleNamespace(email='user@example.com', role='CANDIDATE')

    # patch the service-level references so the already-imported symbols are mocked
    monkeypatch.setattr(
        'app.services.authentication_service.send_otp_service.check_user_existence',
        AsyncMock(return_value=fake_user)
    )
    # deterministic OTP (patch service symbol)
    monkeypatch.setattr('app.services.authentication_service.send_otp_service.generate_otp_code', lambda: '123456')
    # mock email sender to succeed (patch service symbol)
    monkeypatch.setattr('app.services.authentication_service.send_otp_service.send_otp_email', AsyncMock(return_value=True))

    # ensure cache has hset/expire
    fake_cache.hset = AsyncMock()
    fake_cache.expire = AsyncMock()

    svc = SendOtpService(db=fake_db, cache=fake_cache)

    req = SendOTPRequest(email='user@example.com')

    resp = await svc.send_otp(req)

    assert resp["status_code"] == 200
    fake_cache.hset.assert_awaited()
    fake_cache.expire.assert_awaited()


@pytest.mark.asyncio
async def test_send_otp_cache_failure_raises(monkeypatch, fake_db, fake_cache):
    fake_user = SimpleNamespace(email='user@example.com', role='CANDIDATE')
    monkeypatch.setattr(
        'app.services.authentication_service.send_otp_service.check_user_existence',
        AsyncMock(return_value=fake_user)
    )
    monkeypatch.setattr('app.services.authentication_service.send_otp_service.generate_otp_code', lambda: '123456')
    monkeypatch.setattr('app.services.authentication_service.send_otp_service.send_otp_email', AsyncMock(return_value=True))

    # cache hset raises
    fake_cache.hset = AsyncMock(side_effect=Exception('redis down'))
    fake_cache.expire = AsyncMock()

    svc = SendOtpService(db=fake_db, cache=fake_cache)
    req = SendOTPRequest(email='user@example.com')

    with pytest.raises(HTTPException) as exc:
        await svc.send_otp(req)

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_resend_otp_creates_new_when_none(monkeypatch, fake_db, fake_cache):
    # no existing OTP in cache
    fake_cache.hget = AsyncMock(return_value=None)
    fake_cache.hset = AsyncMock()
    fake_cache.expire = AsyncMock()

    # patch the symbols used by the resend service module
    monkeypatch.setattr('app.services.authentication_service.resend_otp_service.generate_otp_code', lambda: '999999')
    monkeypatch.setattr('app.services.authentication_service.resend_otp_service.send_otp_email', AsyncMock(return_value=True))

    svc = ResendOtpService(cache=fake_cache, db=fake_db)
    req = SendOTPRequest(email='user@example.com')

    resp = await svc.resend_otp(req)

    assert resp["status_code"] == 200
    fake_cache.hset.assert_awaited()
    fake_cache.expire.assert_awaited()


@pytest.mark.asyncio
async def test_resend_otp_updates_existing_and_sends(monkeypatch, fake_db, fake_cache):
    # existing OTP present
    existing = {'otp': '000000', 'mode_of_login': 'sign_in'}
    fake_cache.hget = AsyncMock(return_value=json.dumps(existing))
    fake_cache.hset = AsyncMock()
    fake_cache.expire = AsyncMock()

    monkeypatch.setattr('app.services.authentication_service.resend_otp_service.generate_otp_code', lambda: '888888')
    monkeypatch.setattr('app.services.authentication_service.resend_otp_service.send_otp_email', AsyncMock(return_value=True))

    svc = ResendOtpService(cache=fake_cache, db=fake_db)
    req = SendOTPRequest(email='user@example.com')

    resp = await svc.resend_otp(req)

    assert resp["status_code"] == 200
    # ensure that hset was called with updated otp
    assert fake_cache.hset.await_count >= 1
    # inspect last hset call args
    called_args = fake_cache.hset.await_args_list[-1][0]
    # called_args: (cache_key, email, json.dumps(redis_data))
    payload = json.loads(called_args[2])
    assert payload['otp'] == '888888'


@pytest.mark.asyncio
async def test_resend_otp_email_failure_raises(monkeypatch, fake_db, fake_cache):
    fake_cache.hget = AsyncMock(return_value=None)
    fake_cache.hset = AsyncMock()
    fake_cache.expire = AsyncMock()

    monkeypatch.setattr('app.services.authentication_service.resend_otp_service.generate_otp_code', lambda: '777777')
    monkeypatch.setattr('app.services.authentication_service.resend_otp_service.send_otp_email', AsyncMock(return_value=False))

    svc = ResendOtpService(cache=fake_cache, db=fake_db)
    req = SendOTPRequest(email='user@example.com')

    with pytest.raises(HTTPException) as exc:
        await svc.resend_otp(req)

    assert exc.value.status_code == 500
