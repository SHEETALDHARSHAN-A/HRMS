"""
Comprehensive tests for user_repository and scheduling_repository
Targets: user_repository.py (89% -> 100%), scheduling_repository.py (92% -> 100%)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from sqlalchemy.exc import ProgrammingError

from app.db.repository.user_repository import (
    get_user_by_email,
    get_user_by_id,
    delete_users_by_id_and_type,
    update_user_details
)
from app.db.repository.scheduling_repository import (
    create_schedules_batch,
    update_schedule_email_status,
    get_round_name_by_id,
    get_next_round_details
)


# ============================================================================
# user_repository.py Tests (89% -> 100%)
# Missing lines: 31-33, 49, 64-65, 212, 215-217, 226
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_by_email_programming_error_rollback_fails():
    """Test get_user_by_email when rollback itself fails - covers lines 31-33"""
    mock_db = AsyncMock()
    
    # First query raises ProgrammingError
    mock_db.execute.side_effect = [
        ProgrammingError("statement", {}, "error"),
        MagicMock()  # Fallback query succeeds
    ]
    
    # Make rollback fail
    mock_db.rollback.side_effect = Exception("Rollback failed")
    
    # Should handle rollback failure gracefully
    result = await get_user_by_email(mock_db, "test@example.com")
    
    # Should still attempt fallback query
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_user_by_email_fallback_returns_none():
    """Test get_user_by_email when fallback query returns no row - covers line 49"""
    mock_db = AsyncMock()
    
    # First query raises ProgrammingError
    mock_db.execute.side_effect = [
        ProgrammingError("statement", {}, "error"),
        MagicMock()  # Fallback query
    ]
    mock_db.rollback.return_value = None
    
    # Fallback query returns no row
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await get_user_by_email(mock_db, "notfound@example.com")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_duplicate_function():
    """Test the duplicate get_user_by_id function - covers lines 64-65"""
    # Note: There are two get_user_by_id functions in the file (lines 62-65 and 235-238)
    # This tests the first one
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = SimpleNamespace(user_id="u123")
    mock_db.execute.return_value = mock_result
    
    user = await get_user_by_id(mock_db, "u123")
    
    assert user.user_id == "u123"


@pytest.mark.asyncio
async def test_delete_users_role_filtering_admin():
    """Test delete_users_by_id_and_type with ADMIN caller - covers line 212"""
    from app.db.repository.user_repository import delete_users_by_id_and_type
    
    mock_db = AsyncMock()
    
    # Mock users to delete
    mock_users = [
        SimpleNamespace(user_id="u1", role="ADMIN"),
        SimpleNamespace(user_id="u2", role="HR"),
    ]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = mock_users
    mock_db.execute.side_effect = [mock_result, MagicMock(rowcount=2)]
    
    count, users = await delete_users_by_id_and_type(
        mock_db,
        user_ids=["u1", "u2"],
        caller_role="ADMIN",  # ADMIN can delete ADMIN and HR
        caller_id="u3"
    )
    
    assert count == 2
    assert len(users) == 2


@pytest.mark.asyncio
async def test_delete_users_role_filtering_hr():
    """Test delete_users_by_id_and_type with HR caller - covers lines 215-217"""
    from app.db.repository.user_repository import delete_users_by_id_and_type
    
    mock_db = AsyncMock()
    
    mock_users = [SimpleNamespace(user_id="u1", role="HR")]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = mock_users
    mock_db.execute.side_effect = [mock_result, MagicMock(rowcount=1)]
    
    count, users = await delete_users_by_id_and_type(
        mock_db,
        user_ids=["u1"],
        caller_role="HR",  # HR can only delete other HRs
        caller_id="u2"  # Different from u1
    )
    
    assert count == 1


@pytest.mark.asyncio
async def test_delete_users_no_matches():
    """Test delete_users_by_id_and_type when no users match - covers line 226"""
    from app.db.repository.user_repository import delete_users_by_id_and_type
    
    mock_db = AsyncMock()
    
    # No users found
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result
    
    count, users = await delete_users_by_id_and_type(
        mock_db,
        user_ids=["u1", "u2"],
        caller_role="SUPER_ADMIN"
    )
    
    assert count == 0
    assert users == []


# ============================================================================
# scheduling_repository.py Tests (92% -> 100%)
# Missing lines: 80, 98-104, 152, 190
# ============================================================================

@pytest.mark.asyncio
async def test_create_schedules_batch_empty_list():
    """Test create_schedules_batch with empty list - covers line 80"""
    from app.db.repository.scheduling_repository import create_schedules_batch
    
    result = await create_schedules_batch(AsyncMock(), [])
    
    assert result == []


@pytest.mark.asyncio
async def test_create_schedules_batch_type_error_fallback():
    """Test create_schedules_batch when SQLAlchemy raises TypeError - covers lines 88-92"""
    from app.db.repository.scheduling_repository import create_schedules_batch
    
    mock_db = AsyncMock()
    
    schedules_data = [
        {"profile_id": "p1", "job_id": "j1", "round_id": "r1"}
    ]
    
    # Mock Scheduling to raise TypeError
    with patch('app.db.repository.scheduling_repository.Scheduling') as mock_scheduling:
        mock_scheduling.side_effect = TypeError("Cannot instantiate")
        
        result = await create_schedules_batch(mock_db, schedules_data)
        
        # Should fallback to SimpleNamespace and succeed
        assert len(result) == 1


@pytest.mark.asyncio
async def test_create_schedules_batch_add_all_type_error():
    """Test create_schedules_batch when add_all raises TypeError - covers lines 98-101"""
    from app.db.repository.scheduling_repository import create_schedules_batch
    
    mock_db = AsyncMock()
    mock_db.add_all.side_effect = TypeError("add_all not supported")
    mock_db.add = MagicMock()  # Fallback to individual add
    
    schedules_data = [
        {"profile_id": "p1", "job_id": "j1"},
        {"profile_id": "p2", "job_id": "j1"}
    ]
    
    with patch('app.db.repository.scheduling_repository.Scheduling') as mock_scheduling:
        mock_obj1 = SimpleNamespace(profile_id="p1")
        mock_obj2 = SimpleNamespace(profile_id="p2")
        mock_scheduling.side_effect = [mock_obj1, mock_obj2]
        
        result = await create_schedules_batch(mock_db, schedules_data)
        
        # Should use individual add as fallback
        assert mock_db.add.call_count == 2


@pytest.mark.asyncio
async def test_create_schedules_batch_no_add_all_method():
    """Test create_schedules_batch when db has no add_all - covers lines 102-104"""
    from app.db.repository.scheduling_repository import create_schedules_batch
    
    mock_db = AsyncMock()
    # Remove add_all method
    del mock_db.add_all
    mock_db.add = MagicMock()
    
    schedules_data = [{"profile_id": "p1", "job_id": "j1"}]
    
    with patch('app.db.repository.scheduling_repository.Scheduling') as mock_scheduling:
        mock_obj = SimpleNamespace(profile_id="p1")
        mock_scheduling.return_value = mock_obj
        
        result = await create_schedules_batch(mock_db, schedules_data)
        
        # Should use individual add
        assert mock_db.add.called


@pytest.mark.asyncio
async def test_get_round_name_by_id_not_found():
    """Test get_round_name_by_id when round not found - covers line 152"""
    from app.db.repository.scheduling_repository import get_round_name_by_id
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await get_round_name_by_id(mock_db, "550e8400-e29b-41d4-a716-446655440000")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_next_round_details_not_found():
    """Test get_next_round_details when no next round exists - covers line 190"""
    from app.db.repository.scheduling_repository import get_next_round_details
    
    mock_db = AsyncMock()
    
    # First query returns current round order
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = 3  # Current round order
    
    # Second query returns no next round
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = None  # No next round
    
    mock_db.execute.side_effect = [mock_result1, mock_result2]
    
    result = await get_next_round_details(
        mock_db,
        job_id="550e8400-e29b-41d4-a716-446655440000",
        current_round_id="660e8400-e29b-41d4-a716-446655440000"
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_update_user_details_empty_updates():
    """Test update_user_details with empty updates dict"""
    result = await update_user_details(AsyncMock(), "u123", {})
    
    assert result is None
