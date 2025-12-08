"""
Tests for OTP authentication services
Targets: send_otp_service.py (97% -> 100%), resend_otp_service.py (91% -> 100%)
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException, status

from app.services.authentication_service.send_otp_service import SendOtpService
from app.services.authentication_service.resend_otp_service import ResendOtpService
from app.schemas.authentication_request import SendOTPRequest


# ============================================================================
# send_otp_service.py Tests (97% -> 100%)
# Missing line: 56
# ============================================================================

@pytest.mark.asyncio
async def test_send_otp_email_send_fails():
    """Test send_otp when email sending fails - covers line 56"""
    service = SendOtpService(AsyncMock(), AsyncMock())
    
    mock_user = SimpleNamespace(
        email="user@test.com",
        role="CANDIDATE"
    )
    
    mock_request = SendOTPRequest(email="user@test.com")
    
    with patch('app.services.authentication_service.send_otp_service.check_user_existence') as mock_check:
        with patch('app.services.authentication_service.send_otp_service.send_otp_email') as mock_email:
            mock_check.return_value = mock_user
            mock_email.return_value = False  # Email send fails
            
            with pytest.raises(HTTPException) as exc_info:
                await service.send_otp(mock_request)
            
            assert exc_info.value.status_code == 500
            assert "Failed to send OTP email" in exc_info.value.detail


# ============================================================================
# resend_otp_service.py Tests (91% -> 100%)
# Missing lines: 57-59, 63
# ============================================================================

@pytest.mark.asyncio
async def test_resend_otp_redis_update_fails():
    """Test resend_otp when Redis update fails - covers lines 57-59"""
    mock_cache = AsyncMock()
    service = ResendOtpService(mock_cache, AsyncMock())
    
    # Simulate existing OTP
    existing_data = json.dumps({"otp": "123456"})
    mock_cache.hget.return_value = existing_data
    
    # Make hset fail
    mock_cache.hset.side_effect = Exception("Redis connection error")
    
    mock_request = SendOTPRequest(email="user@test.com")
    
    with pytest.raises(HTTPException) as exc_info:
        await service.resend_otp(mock_request)
    
    assert exc_info.value.status_code == 500
    assert "Failed to resend OTP" in exc_info.value.detail


@pytest.mark.asyncio
async def test_resend_otp_email_send_fails():
    """Test resend_otp when email sending fails - covers line 63"""
    mock_cache = AsyncMock()
    service = ResendOtpService(mock_cache, AsyncMock())
    
    # Simulate existing OTP
    existing_data = json.dumps({"otp": "123456"})
    mock_cache.hget.return_value = existing_data
    mock_cache.hset.return_value = True
    mock_cache.expire.return_value = True
    
    mock_request = SendOTPRequest(email="user@test.com")
    
    with patch('app.services.authentication_service.resend_otp_service.send_otp_email') as mock_email:
        mock_email.return_value = False  # Email send fails
        
        with pytest.raises(HTTPException) as exc_info:
            await service.resend_otp(mock_request)
        
        assert exc_info.value.status_code == 500
        assert "Failed to send OTP email" in exc_info.value.detail


@pytest.mark.asyncio
async def test_resend_otp_success_with_existing_otp():
    """Test successful OTP resend with existing OTP"""
    mock_cache = AsyncMock()
    service = ResendOtpService(mock_cache, AsyncMock())
    
    existing_data = json.dumps({"otp": "old123"})
    mock_cache.hget.return_value = existing_data
    mock_cache.hset.return_value = True
    mock_cache.expire.return_value = True
    
    mock_request = SendOTPRequest(email="user@test.com")
    
    with patch('app.services.authentication_service.resend_otp_service.send_otp_email') as mock_email:
        mock_email.return_value = True
        
        result = await service.resend_otp(mock_request)
        
        assert result['success'] is True
        assert result['status_code'] == 200
        assert 'OTP sent successfully' in result['message']


@pytest.mark.asyncio
async def test_resend_otp_success_no_existing_otp():
    """Test successful OTP resend when no existing OTP - new session"""
    mock_cache = AsyncMock()
    service = ResendOtpService(mock_cache, AsyncMock())
    
    # No existing OTP
    mock_cache.hget.return_value = None
    mock_cache.hset.return_value = True
    mock_cache.expire.return_value = True
    
    mock_request = SendOTPRequest(email="newuser@test.com")
    
    with patch('app.services.authentication_service.resend_otp_service.send_otp_email') as mock_email:
        mock_email.return_value = True
        
        result = await service.resend_otp(mock_request)
        
        assert result['success'] is True
        assert 'OTP sent successfully' in result['message']
