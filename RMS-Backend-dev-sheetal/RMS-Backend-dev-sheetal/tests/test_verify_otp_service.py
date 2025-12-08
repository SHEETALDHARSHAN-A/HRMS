import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException, Response

from app.schemas.authentication_request import VerifyOTPRequest
from app.services.authentication_service.verify_otp_service import VerifyOtpService


@pytest.mark.asyncio
async def test_verify_otp_not_found_raises(fake_db, fake_cache):
    # OTP missing in cache
    fake_cache.hget = AsyncMock(return_value=None)

    svc = VerifyOtpService(db=fake_db, cache=fake_cache)
    req = VerifyOTPRequest(email='user@example.com', otp='123456')
    resp = Response()

    with pytest.raises(HTTPException) as exc:
        await svc.verify_otp(req, resp)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_otp_invalid_otp_raises(fake_db, fake_cache):
    payload = {'otp': '000000', 'mode_of_login': 'sign_in', 'email': 'user@example.com'}
    fake_cache.hget = AsyncMock(return_value=json.dumps(payload))

    svc = VerifyOtpService(db=fake_db, cache=fake_cache)
    req = VerifyOTPRequest(email='user@example.com', otp='123456')
    resp = Response()

    with pytest.raises(HTTPException) as exc:
        await svc.verify_otp(req, resp)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_otp_sign_in_success(monkeypatch, fake_db, fake_cache):
    # OTP matches and user exists
    payload = {
        'otp': '123456',
        'mode_of_login': 'sign_in',
        'email': 'user@example.com',
        'first_name': 'Jane',
        'last_name': 'Doe',
        'role': 'CANDIDATE'
    }
    fake_cache.hget = AsyncMock(return_value=json.dumps(payload))
    fake_cache.hdel = AsyncMock()
    fake_cache.sadd = AsyncMock()
    fake_cache.expire = AsyncMock()

    # user returned by DB
    fake_user = SimpleNamespace(user_id='abc-123', role='CANDIDATE', first_name='Jane', last_name='Doe')

    # patch service-level functions and token creators
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.check_user_existence', AsyncMock(return_value=fake_user))
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.create_access_token', lambda uid, role, **k: 'access.jwt')
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.create_refresh_token', lambda uid, role: 'refresh.jwt')
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.get_jti_from_token', lambda t: ('jti-refresh' if 'refresh' in t else 'jti-access'))

    svc = VerifyOtpService(db=fake_db, cache=fake_cache)
    req = VerifyOTPRequest(email='user@example.com', otp='123456')
    resp = Response()

    result = await svc.verify_otp(req, resp)

    assert result['status_code'] == 200
    # cookies should be set on the Response (may produce multiple Set-Cookie headers)
    cookie_headers = [v.decode() for k, v in resp.raw_headers if k.decode().lower() == 'set-cookie']
    assert any('access_token=' in c for c in cookie_headers)
    assert any('refresh_token=' in c for c in cookie_headers)
    fake_cache.hdel.assert_awaited()
    fake_cache.sadd.assert_awaited()


@pytest.mark.asyncio
async def test_verify_otp_sign_up_creates_user(monkeypatch, fake_db, fake_cache):
    payload = {
        'otp': '222222',
        'mode_of_login': 'sign_up',
        'email': 'new@example.com',
        'first_name': 'New',
        'last_name': 'User',
        'role': 'CANDIDATE'
    }
    fake_cache.hget = AsyncMock(return_value=json.dumps(payload))
    fake_cache.hdel = AsyncMock()
    fake_cache.sadd = AsyncMock()
    fake_cache.expire = AsyncMock()

    # check_user_existence should indicate no existing user
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.check_user_existence', AsyncMock(return_value=None))
    # simulate creating user from cache
    created_user = SimpleNamespace(user_id='new-1', role='CANDIDATE', first_name='New', last_name='User')
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.create_user_from_cache', AsyncMock(return_value=created_user))

    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.create_access_token', lambda uid, role, **k: 'access.jwt')
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.create_refresh_token', lambda uid, role: 'refresh.jwt')
    monkeypatch.setattr('app.services.authentication_service.verify_otp_service.get_jti_from_token', lambda t: ('jti-refresh' if 'refresh' in t else 'jti-access'))

    svc = VerifyOtpService(db=fake_db, cache=fake_cache)
    req = VerifyOTPRequest(email='new@example.com', otp='222222')
    resp = Response()

    result = await svc.verify_otp(req, resp)

    assert result['status_code'] == 200
    cookie_headers = [v.decode() for k, v in resp.raw_headers if k.decode().lower() == 'set-cookie']
    assert any('access_token=' in c for c in cookie_headers)
    assert any('refresh_token=' in c for c in cookie_headers)
    fake_cache.hdel.assert_awaited()
    fake_cache.sadd.assert_awaited()
