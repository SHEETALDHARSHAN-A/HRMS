import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.job_post.career_application_service import CareerApplicationService
from app.utils.standard_response_utils import ResponseBuilder


@pytest.mark.asyncio
async def test_send_otp_redis_failure(fake_cache):
    # Simulate Redis hset raising
    async def bad_hset(k, field, v):
        raise Exception('redis fail')
    fake_cache.hset = AsyncMock(side_effect=bad_hset)
    fake_cache.expire = AsyncMock()

    svc = CareerApplicationService(fake_cache)
    res = await svc.send_otp('j1', 'e@x.com')
    assert res['status_code'] == 500
    assert 'Failed to store OTP' in res['message']


@pytest.mark.asyncio
async def test_send_otp_email_failure_returns_500(fake_cache):
    # Simulate successful redis, but send_otp_email returns False
    fake_cache.hset = AsyncMock(return_value=1)
    fake_cache.expire = AsyncMock(return_value=1)

    async def fake_send_otp_email(email, otp, subject, db=None):
        return False

    with patch('app.services.job_post.career_application_service.send_otp_email', AsyncMock(side_effect=fake_send_otp_email)):
        svc = CareerApplicationService(fake_cache)
        res = await svc.send_otp('j1', 'e@x.com')
        assert res['status_code'] == 500
        assert 'Failed to send OTP email' in res['message']


@pytest.mark.asyncio
async def test_send_otp_email_raises_exception(fake_cache):
    fake_cache.hset = AsyncMock(return_value=1)
    fake_cache.expire = AsyncMock(return_value=1)

    async def raise_send_otp(email, otp, subject, db=None):
        raise Exception('smtp error')

    with patch('app.services.job_post.career_application_service.send_otp_email', AsyncMock(side_effect=raise_send_otp)):
        svc = CareerApplicationService(fake_cache)
        res = await svc.send_otp('j1', 'e@x.com')
        assert res['status_code'] == 500
        assert 'Failed to send OTP email' in res['message']


@pytest.mark.asyncio
async def test_verify_otp_json_decode_error(fake_cache):
    # When Redis returns invalid JSON for stored OTP, JSONDecodeError should be handled
    fake_cache.hget = AsyncMock(return_value='not-json')
    svc = CareerApplicationService(fake_cache)
    res = await svc.verify_otp_and_submit_application('j1', 'e@x.com', '123', {})
    assert res['status_code'] == 500
    assert 'Invalid stored data' in res['message']


@pytest.mark.asyncio
async def test_verify_otp_deletes_cache_on_success(fake_cache):
    stored = json.dumps({'otp': '123'})
    fake_cache.hget = AsyncMock(return_value=stored)
    fake_cache.delete = AsyncMock()

    svc = CareerApplicationService(fake_cache)
    # simulate no duplicate profile in DB
    # pass a simple db with scalars().first returning None
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars().first.return_value = None
    mock_db.execute.return_value = mock_res

    res = await svc.verify_otp_and_submit_application('j1', 'e@x.com', '123', {'application_id': 'app1'}, db=mock_db)
    assert res['status_code'] == 200
    fake_cache.delete.assert_called()
    assert res['data']['application_id'] == 'app1'
