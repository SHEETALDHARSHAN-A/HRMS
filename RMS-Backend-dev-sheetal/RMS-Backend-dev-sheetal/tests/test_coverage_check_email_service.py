import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException, status

from app.services.authentication_service.check_email_service import CheckUserExistenceService


@pytest.mark.asyncio
async def test_check_email_status_invalid_format():
    """Test check_email_status with invalid email format"""
    service = CheckUserExistenceService(AsyncMock())
    
    with patch('app.services.authentication_service.check_email_service.validate_input_email') as mock_validate:
        # Simulate validation raising HTTPException
        mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid")
        
        result = await service.check_email_status("invalid-email")
        
        assert result['success'] is False
        assert result['status_code'] == status.HTTP_400_BAD_REQUEST
        assert "Invalid email format" in result['message']
        assert result['data']['is_available'] is False
        assert result['data']['user_status'] == "INVALID_FORMAT"


@pytest.mark.asyncio
async def test_check_email_status_user_exists():
    """Test check_email_status when user exists"""
    service = CheckUserExistenceService(AsyncMock())
    
    # Create mock user
    mock_user = SimpleNamespace(
        user_id="u1",
        email="test@example.com",
        role="CANDIDATE"
    )
    
    with patch('app.services.authentication_service.check_email_service.validate_input_email'):
        with patch('app.services.authentication_service.check_email_service.get_user_by_email') as mock_get:
            mock_get.return_value = mock_user
            
            result = await service.check_email_status("test@example.com")
            
            assert result['success'] is True
            assert result['status_code'] == status.HTTP_200_OK
            assert "User with this email exists" in result['message']
            assert result['data']['is_available'] is False
            assert result['data']['user_status'] == "EXIST"


@pytest.mark.asyncio
async def test_check_email_status_user_not_exists():
    """Test check_email_status when user does not exist"""
    service = CheckUserExistenceService(AsyncMock())
    
    with patch('app.services.authentication_service.check_email_service.validate_input_email'):
        with patch('app.services.authentication_service.check_email_service.get_user_by_email') as mock_get:
            mock_get.return_value = None
            
            result = await service.check_email_status("new@example.com")
            
            assert result['success'] is False
            assert result['status_code'] == status.HTTP_403_FORBIDDEN
            assert "User with this email does not exist" in result['message']
            assert result['data']['is_available'] is True
            assert result['data']['user_status'] == "NOT_EXIST"


@pytest.mark.asyncio
async def test_check_email_status_email_normalization():
    """Test that email is normalized (trimmed and lowercased)"""
    service = CheckUserExistenceService(AsyncMock())
    
    with patch('app.services.authentication_service.check_email_service.validate_input_email'):
        with patch('app.services.authentication_service.check_email_service.get_user_by_email') as mock_get:
            mock_get.return_value = None
            
            await service.check_email_status("  TEST@EXAMPLE.COM  ")
            
            # Verify get_user_by_email was called with normalized email
            mock_get.assert_called_once_with(service.db, "test@example.com")


@pytest.mark.asyncio
async def test_check_email_status_logging_exception_handling():
    """Test that logging exceptions don't break the flow"""
    service = CheckUserExistenceService(AsyncMock())
    
    # Create mock user that will cause logging to fail
    mock_user = MagicMock()
    mock_user.user_id = property(MagicMock(side_effect=Exception("Logging failed")))
    
    with patch('app.services.authentication_service.check_email_service.validate_input_email'):
        with patch('app.services.authentication_service.check_email_service.get_user_by_email') as mock_get:
            mock_get.return_value = mock_user
            
            # Should not raise exception despite logging error
            result = await service.check_email_status("test@example.com")
            
            # Should still return successful result
            assert result['success'] is True
            assert result['status_code'] == status.HTTP_200_OK
