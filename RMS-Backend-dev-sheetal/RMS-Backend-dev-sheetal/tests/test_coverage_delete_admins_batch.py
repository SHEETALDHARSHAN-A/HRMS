import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException, status

from app.services.admin_service.delete_admins_batch_service import DeleteAdminsBatchService
from app.schemas.authentication_request import DeleteAdminsBatchRequest


@pytest.mark.asyncio
async def test_delete_admins_no_user_ids():
    """Test delete_admins with empty user_ids list"""
    service = DeleteAdminsBatchService(AsyncMock())
    request = DeleteAdminsBatchRequest(user_ids=[])
    
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_admins(request)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "No user IDs provided" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_admins_no_matching_accounts():
    """Test delete_admins when no matching accounts are found"""
    service = DeleteAdminsBatchService(AsyncMock())
    request = DeleteAdminsBatchRequest(user_ids=["u1", "u2"])
    
    with patch('app.services.admin_service.delete_admins_batch_service.delete_users_by_id_and_type') as mock_delete:
        # Return 0 deleted count
        mock_delete.return_value = (0, [])
        
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_admins(request)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "No matching Admin accounts found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_admins_success():
    """Test successful deletion of admin accounts"""
    service = DeleteAdminsBatchService(AsyncMock())
    request = DeleteAdminsBatchRequest(user_ids=["u1", "u2"])
    
    # Create mock deleted users
    user1 = SimpleNamespace(user_id="u1", first_name="John", last_name="Doe", email="john@test.com")
    user2 = SimpleNamespace(user_id="u2", first_name="Jane", last_name="Smith", email="jane@test.com")
    
    with patch('app.services.admin_service.delete_admins_batch_service.delete_users_by_id_and_type') as mock_delete:
        with patch('app.services.admin_service.delete_admins_batch_service.send_admin_removal_email') as mock_email:
            mock_delete.return_value = (2, [user1, user2])
            mock_email.return_value = AsyncMock()
            
            result = await service.delete_admins(request, caller_role="SUPER_ADMIN", caller_id="admin1")
            
            assert result['success'] is True
            assert result['status_code'] == status.HTTP_200_OK
            assert result['data']['deleted_count'] == 2
            assert len(result['data']['deleted_ids']) == 2
            assert "Successfully deleted 2 admin accounts" in result['message']
            
            # Verify email was sent for both users
            assert mock_email.call_count == 2


@pytest.mark.asyncio
async def test_delete_admins_with_caller_info():
    """Test delete_admins passes caller role and ID correctly"""
    service = DeleteAdminsBatchService(AsyncMock())
    request = DeleteAdminsBatchRequest(user_ids=["u1"])
    
    user1 = SimpleNamespace(user_id="u1", first_name="Test", last_name="User", email="test@test.com")
    
    with patch('app.services.admin_service.delete_admins_batch_service.delete_users_by_id_and_type') as mock_delete:
        with patch('app.services.admin_service.delete_admins_batch_service.send_admin_removal_email') as mock_email:
            mock_delete.return_value = (1, [user1])
            mock_email.return_value = AsyncMock()
            
            await service.delete_admins(request, caller_role="ADMIN", caller_id="admin123")
            
            # Verify caller_role and caller_id were passed
            mock_delete.assert_called_once_with(
                service.db,
                ["u1"],
                allowed_roles=["SUPER_ADMIN", "ADMIN", "HR"],
                caller_role="ADMIN",
                caller_id="admin123"
            )
