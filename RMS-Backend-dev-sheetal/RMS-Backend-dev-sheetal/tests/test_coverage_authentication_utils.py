"""
Comprehensive tests for authentication utilities with edge cases.
Target: authentication_utils.py (90% -> 100%)
Missing lines: 68-69, 86-87, 107-108
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import redis.asyncio as redis

from app.utils.authentication_utils import (
    generate_otp_code,
    get_jti_from_token,
    is_jti_revoked,
    create_access_token,
    create_refresh_token
)

# Mock the constant to avoid import errors or side effects
with patch('app.utils.authentication_utils.JWT_BLOCKLIST_KEY', 'blacklist:'):
    pass


# ============================================================================
# generate_otp_code Tests - Lines 68-69
# ============================================================================

def test_generate_otp_code_invalid_length_string():
    """Test OTP generation with invalid length (string) - covers lines 68-69"""
    # Pass a non-numeric string that will fail int() conversion
    otp = generate_otp_code(length="invalid")
    
    # Should fallback to default length 6
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_otp_code_invalid_length_none():
    """Test OTP generation with None length - covers exception path"""
    otp = generate_otp_code(length=None)
    
    # Should fallback to default length 6
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_otp_code_clamped_too_high():
    """Test OTP generation with length > 12 (clamped to 12)"""
    otp = generate_otp_code(length=20)
    
    # Should be clamped to 12
    assert len(otp) == 12
    assert otp.isdigit()


def test_generate_otp_code_clamped_too_low():
    """Test OTP generation with length < 4 (clamped to 4)"""
    otp = generate_otp_code(length=2)
    
    # Should be clamped to 4
    assert len(otp) == 4
    assert otp.isdigit()


# ============================================================================
# get_jti_from_token Tests - Lines 86-87
# ============================================================================

def test_get_jti_from_token_invalid_signature():
    """Test JTI extraction with invalid signature - covers lines 86-87"""
    # Create a token with wrong signature
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwianRpIjoiYWJjMTIzIn0.invalid_signature"
    
    result = get_jti_from_token(invalid_token)
    
    # Should return None on JWTError
    assert result is None


def test_get_jti_from_token_malformed():
    """Test JTI extraction with malformed token"""
    malformed_token = "not.a.valid.jwt.token"
    
    result = get_jti_from_token(malformed_token)
    
    assert result is None


def test_get_jti_from_token_empty_string():
    """Test JTI extraction with empty token"""
    result = get_jti_from_token("")
    
    assert result is None


def test_get_jti_from_token_valid_expired():
    """Test JTI extraction from expired but valid token"""
    # Create an expired token
    token = create_access_token("user123", "ADMIN")
    
    # Mock expired token by creating one with past expiry
    from datetime import datetime, timedelta
    from jose import jwt
    from app.config.app_config import AppConfig
    
    settings = AppConfig()
    expired_payload = {
        "sub": "user123",
        "role": "ADMIN",
        "jti": "test-jti-123",
        "exp": datetime.utcnow() - timedelta(days=1)  # Expired yesterday
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
    
    # Should still extract JTI even though expired (verify_exp=False)
    result = get_jti_from_token(expired_token)
    
    assert result == "test-jti-123"


# ============================================================================
# is_jti_revoked Tests - Lines 107-108
# ============================================================================

@pytest.mark.asyncio
async def test_is_jti_revoked_redis_exception():
    """Test is_jti_revoked exception handling - covers lines 107-108"""
    mock_cache = AsyncMock()
    # FIX: Mock 'exists' instead of 'get' because is_jti_revoked calls cache.exists
    mock_cache.exists.side_effect = Exception("Redis error")
    
    # Should handle exception gracefully and return False
    result = await is_jti_revoked("test_jti", mock_cache)
    
    # When Redis fails, assume not revoked for safety
    assert result is False


@pytest.mark.asyncio
async def test_is_jti_revoked_not_found():
    """Test is_jti_revoked when JTI not found (not revoked)"""
    mock_cache = AsyncMock()
    # FIX: Mock 'exists' instead of 'get'
    mock_cache.exists.return_value = 0  # Redis exists returns 0 if not found
    
    result = await is_jti_revoked("test_jti", mock_cache)
    
    # 0 is falsy, so it should return 0 (which is treated as False)
    assert result == 0 or result is False


@pytest.mark.asyncio
async def test_is_jti_revoked_cache_none():
    """Test is_jti_revoked when cache is None"""
    result = await is_jti_revoked("jti789", None)
    
    assert result is False


@pytest.mark.asyncio
async def test_is_jti_revoked_success():
    """Test successful JTI revocation check"""
    mock_cache = AsyncMock()
    # FIX: Mock 'exists' to return 1 (True)
    mock_cache.exists.return_value = 1
    
    result = await is_jti_revoked("revoked-jti", mock_cache)
    
    assert result == 1 or result is True
