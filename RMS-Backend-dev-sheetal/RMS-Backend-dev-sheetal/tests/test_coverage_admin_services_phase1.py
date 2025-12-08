"""
Comprehensive tests for admin service files with low coverage.
Targets: get_admin_by_id_service.py, get_all_admins_service.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException, status

from app.services.admin_service.get_admin_by_id_service import GetAdminByIdService
from app.services.admin_service.get_all_admins_service import GetAllAdminsService


# ============================================================================
# get_admin_by_id_service.py Tests (58% -> 100%)
# Missing lines: 11, 14-22
# ============================================================================

@pytest.mark.asyncio
async def test_get_admin_by_id_user_not_found():
    """Test get_admin_details when user doesn't exist - covers lines 14, 16-20"""
    service = GetAdminByIdService(AsyncMock())
    
    with patch('app.services.admin_service.get_admin_by_id_service.get_user_by_id') as mock_get:
        mock_get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_admin_details("user123")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_admin_by_id_user_is_candidate():
    """Test get_admin_details when user is CANDIDATE (not admin) - covers lines 14, 16-20"""
    service = GetAdminByIdService(AsyncMock())
    
    mock_user = SimpleNamespace(
        user_id="u1",
        role="CANDIDATE",  # Not an admin role
        first_name="John",
        last_name="Doe",
        email="john@test.com"
    )
    
    with patch('app.services.admin_service.get_admin_by_id_service.get_user_by_id') as mock_get:
        mock_get.return_value = mock_user
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_admin_details("u1")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_admin_by_id_success_super_admin():
    """Test successful retrieval of SUPER_ADMIN - covers lines 11, 14, 16, 22-33"""
    service = GetAdminByIdService(AsyncMock())
    
    mock_user = SimpleNamespace(
        user_id="u1",
        role="SUPER_ADMIN",
        first_name="Admin",
        last_name="User",
        email="admin@test.com",
        phone_number="+1234567890"
    )
    
    with patch('app.services.admin_service.get_admin_by_id_service.get_user_by_id') as mock_get:
        mock_get.return_value = mock_user
        
        result = await service.get_admin_details("u1")
        
        assert result['success'] is True
        assert result['status_code'] == status.HTTP_200_OK
        assert result['data']['user_id'] == "u1"
        assert result['data']['role'] == "SUPER_ADMIN"
        assert result['data']['phone_number'] == "+1234567890"


@pytest.mark.asyncio
async def test_get_admin_by_id_success_admin_role():
    """Test successful retrieval of ADMIN - covers line 16 (ADMIN in list)"""
    service = GetAdminByIdService(AsyncMock())
    
    mock_user = SimpleNamespace(
        user_id="u2",
        role="ADMIN",
        first_name="Regular",
        last_name="Admin",
        email="admin2@test.com",
        phone_number=None  # Test missing phone_number
    )
    
    with patch('app.services.admin_service.get_admin_by_id_service.get_user_by_id') as mock_get:
        mock_get.return_value = mock_user
        
        result = await service.get_admin_details("u2")
        
        assert result['success'] is True
        assert result['data']['role'] == "ADMIN"
        assert result['data']['phone_number'] is None


@pytest.mark.asyncio
async def test_get_admin_by_id_success_hr_role():
    """Test successful retrieval of HR - covers line 16 (HR in list)"""
    service = GetAdminByIdService(AsyncMock())
    
    mock_user = SimpleNamespace(
        user_id="u3",
        role="HR",
        first_name="HR",
        last_name="Rep",
        email="hr@test.com"
    )
    
    with patch('app.services.admin_service.get_admin_by_id_service.get_user_by_id') as mock_get:
        mock_get.return_value = mock_user
        
        result = await service.get_admin_details("u3")
        
        assert result['success'] is True
        assert result['data']['role'] == "HR"


# ============================================================================
# get_all_admins_service.py Tests (70% -> 100%)
# Missing lines: 11, 20-22
# ============================================================================

@pytest.mark.asyncio
async def test_get_all_admins_success():
    """Test successful retrieval of all admins - covers lines 11, 20-22"""
    service = GetAllAdminsService(AsyncMock())
    
    mock_admins = [
        {"user_id": "u1", "role": "SUPER_ADMIN", "email": "admin1@test.com"},
        {"user_id": "u2", "role": "ADMIN", "email": "admin2@test.com"},
    ]
    
    with patch('app.services.admin_service.get_all_admins_service.get_all_admins_details') as mock_get:
        mock_get.return_value = mock_admins
        
        result = await service.get_all_admins(caller_role="SUPER_ADMIN")
        
        assert result['success'] is True
        assert result['status_code'] == status.HTTP_200_OK
        assert result['data']['admins'] == mock_admins
        assert len(result['data']['admins']) == 2


@pytest.mark.asyncio
async def test_get_all_admins_with_role_filtering():
    """Test admin retrieval with role-based filtering"""
    service = GetAllAdminsService(AsyncMock())
    
    mock_admins = [
        {"user_id": "u1", "role": "ADMIN", "email": "admin@test.com"},
        {"user_id": "u2", "role": "HR", "email": "hr@test.com"},
    ]
    
    with patch('app.services.admin_service.get_all_admins_service.get_all_admins_details') as mock_get:
        mock_get.return_value = mock_admins
        
        result = await service.get_all_admins(caller_role="ADMIN")
        
        assert result['success'] is True
        assert result['data']['admins'] == mock_admins


@pytest.mark.asyncio
async def test_get_all_admins_empty_list():
    """Test when no admins are found"""
    service = GetAllAdminsService(AsyncMock())
    
    with patch('app.services.admin_service.get_all_admins_service.get_all_admins_details') as mock_get:
        mock_get.return_value = []
        
        result = await service.get_all_admins(caller_role="HR")
        
        assert result['success'] is True
        assert result['data']['admins'] == []
