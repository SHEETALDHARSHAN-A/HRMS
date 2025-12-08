import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.job_post.career_application_service import CareerApplicationService

@pytest.mark.asyncio
async def test_send_otp_duplicate_check_fail(fake_cache):
    # Mock DB session to return existing profile
    mock_session = AsyncMock()
    # Async context manager protocol: async with mock_session() as db -> db should be mock_session
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    mock_result = MagicMock()
    mock_result.scalars().first.return_value = True # Exists
    mock_session.execute.return_value = mock_result
    
    # Patch both the session factory and the local 'select' symbol so the
    # test does not attempt to construct real SQLAlchemy expressions.
    class FakeSelect:
        def __init__(self, *a, **k):
            pass
        def where(self, *a, **k):
            return self

    with patch("app.services.job_post.career_application_service.AsyncSessionLocal", return_value=mock_session), \
         patch("app.services.job_post.career_application_service.select", FakeSelect):
        svc = CareerApplicationService(fake_cache)
        res = await svc.send_otp("job1", "a@b.com")
        
        assert res["status_code"] == 409

@pytest.mark.asyncio
async def test_verify_otp_not_found(fake_cache):
    fake_cache.hget = AsyncMock(return_value=None)
    svc = CareerApplicationService(fake_cache)
    
    res = await svc.verify_otp_and_submit_application("job1", "a@b.com", "123", {})
    assert res["status_code"] == 400
    assert "Invalid" in res["message"]

@pytest.mark.asyncio
async def test_verify_otp_mismatch(fake_cache):
    stored = json.dumps({"otp": "999"})
    fake_cache.hget = AsyncMock(return_value=stored)
    svc = CareerApplicationService(fake_cache)
    
    res = await svc.verify_otp_and_submit_application("job1", "a@b.com", "111", {})
    assert res["status_code"] == 400
    assert "Invalid OTP" in res["message"]

@pytest.mark.asyncio
async def test_verify_otp_duplicate_check_fail(fake_cache):
    stored = json.dumps({"otp": "123"})
    fake_cache.hget = AsyncMock(return_value=stored)
    fake_cache.delete = AsyncMock()
    
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars().first.return_value = True # Duplicate profile found
    mock_db.execute.return_value = mock_res

    # Patch module 'select' to avoid SQLAlchemy coercion during unit test
    class FakeSelect:
        def __init__(self, *a, **k):
            pass
        def where(self, *a, **k):
            return self

    svc = CareerApplicationService(fake_cache)
    with patch("app.services.job_post.career_application_service.select", FakeSelect):
        res = await svc.verify_otp_and_submit_application("job1", "a@b.com", "123", {}, db=mock_db)
    
    assert res["status_code"] == 409