"""
Comprehensive tests for notification service and shortlist controller
Targets: notification_service.py (83% -> 100%), shortlist_controller.py (86% -> 100%)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException, status

from app.services.notification.notification_service import NotificationService
from app.controllers.shortlist_controller import (
    get_job_round_overview_controller,
    get_all_candidates_controller,
    update_candidate_status_controller
)


# ============================================================================
# notification_service.py Tests (83% -> 100%)
# Missing lines: 35, 62-63, 69-70, 76-77, 85-86
# ============================================================================

@pytest.mark.asyncio
async def test_get_notifications_with_related_invitation():
    """Test get_notifications when notification has related_invitation_id - covers line 35"""
    service = NotificationService(AsyncMock())
    
    mock_notification = SimpleNamespace(
        notification_id="n1",
        type="invitation",
        title="Test",
        message="Message",
        is_read=False,
        created_at=None,
        read_at=None,
        related_invitation_id="inv123",  # Has invitation ID
        related_user_id=None
    )
    
    with patch('app.services.notification.notification_service.fetch_notifications') as mock_fetch:
        mock_fetch.return_value = [mock_notification]
        
        result = await service.get_notifications("user123")
        
        assert result['success'] is True
        assert result['data']['notifications'][0]['related_invitation_id'] == "inv123"


@pytest.mark.asyncio
async def test_mark_notification_as_read_exception():
    """Test mark_notification_as_read when exception occurs - covers lines 62-63"""
    service = NotificationService(AsyncMock())
    
    with patch('app.services.notification.notification_service.mark_notification_read_db') as mock_mark:
        mock_mark.side_effect = Exception("Database error")
        
        result = await service.mark_notification_as_read("notif123", "user123")
        
        assert result['success'] is False
        assert result['status_code'] == 500
        assert 'Failed to mark notification as read' in result['message']


@pytest.mark.asyncio
async def test_mark_all_notifications_as_read_exception():
    """Test mark_all_notifications_as_read when exception occurs - covers lines 69-70"""
    service = NotificationService(AsyncMock())
    
    with patch('app.services.notification.notification_service.mark_all_notifications_read_db') as mock_mark:
        mock_mark.side_effect = Exception("DB connection lost")
        
        result = await service.mark_all_notifications_as_read("user123")
        
        assert result['success'] is False
        assert result['status_code'] == 500
        assert 'Failed to mark all notifications as read' in result['message']


@pytest.mark.asyncio
async def test_get_unread_count_exception():
    """Test get_unread_count when exception occurs - covers lines 76-77"""
    service = NotificationService(AsyncMock())
    
    with patch('app.services.notification.notification_service.get_unread_count_db') as mock_count:
        mock_count.side_effect = Exception("Query failed")
        
        result = await service.get_unread_count("user123")
        
        assert result['success'] is False
        assert result['status_code'] == 500
        assert 'Failed to get unread count' in result['message']


@pytest.mark.asyncio
async def test_delete_notification_exception():
    """Test delete_notification when exception occurs - covers lines 85-86"""
    service = NotificationService(AsyncMock())
    
    with patch('app.services.notification.notification_service.delete_notification_db') as mock_delete:
        mock_delete.side_effect = Exception("Delete operation failed")
        
        result = await service.delete_notification("notif456", "user123")
        
        assert result['success'] is False
        assert result['status_code'] == 500
        assert 'Failed to delete notification' in result['message']


# ============================================================================
# shortlist_controller.py Tests (86% -> 100%)
# Missing lines: 42, 70, 80-82, 113-115
# ============================================================================

@pytest.mark.asyncio
async def test_get_job_round_overview_http_exception():
    """Test get_job_round_overview_controller when HTTPException raised - covers line 42"""
    with patch('app.controllers.shortlist_controller.ShortlistService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.get_job_round_overview.side_effect = HTTPException(
            status_code=403,
            detail="Forbidden"
        )
        mock_service_class.return_value = mock_service
        
        result = await get_job_round_overview_controller(AsyncMock())
        
        assert result['success'] is False
        assert result['status_code'] == 403
        assert 'Forbidden' in result['errors'][0]


@pytest.mark.asyncio
async def test_get_all_candidates_with_result_filter():
    """Test get_all_candidates_controller with result_filter - covers line 70"""
    with patch('app.controllers.shortlist_controller.ShortlistService') as mock_service_class:
        mock_service = MagicMock()
        mock_candidates = [{"name": "John Doe", "status": "shortlisted"}]
        mock_service.get_candidates_by_job_and_round.return_value = mock_candidates
        mock_service_class.return_value = mock_service
        
        result = await get_all_candidates_controller(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            round_id="660e8400-e29b-41d4-a716-446655440000",
            result_filter="shortlisted",  # Non-"all" filter
            db=AsyncMock()
        )
        
        assert result['success'] is True
        assert 'shortlisted candidates' in result['message'].lower()


@pytest.mark.asyncio
async def test_get_all_candidates_http_exception():
    """Test get_all_candidates_controller when HTTPException raised - covers line 78-79"""
    # HTTPException should be caught, but if it happens during validation it gets handled
    result = await get_all_candidates_controller(
        job_id="invalid-uuid",  # Bad UUID will trigger HTTPException
        round_id="660e8400-e29b-41d4-a716-446655440000",
        result_filter="all",
        db=AsyncMock()
    )
    
    assert result['success'] is False
    assert result['status_code'] == 400


@pytest.mark.asyncio
async def test_get_all_candidates_general_exception():
    """Test get_all_candidates_controller when general exception occurs - covers lines 80-82"""
    with patch('app.controllers.shortlist_controller.ShortlistService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.get_candidates_by_job_and_round.side_effect = Exception("DB connection error")
        mock_service_class.return_value = mock_service
        
        result = await get_all_candidates_controller(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            round_id="660e8400-e29b-41d4-a716-446655440000",
            result_filter="all",
            db=AsyncMock()
        )
        
        assert result['success'] is False
        assert result['status_code'] == 500
        assert 'Failed to fetch candidates' in result['message']


@pytest.mark.asyncio
async def test_update_candidate_status_http_exception():
    """Test update_candidate_status_controller when HTTPException raised - covers line 111-112"""
    # Invalid UUID will trigger HTTPException from validation
    mock_input = MagicMock()
    mock_input.new_result = "shortlisted"
    
    result = await update_candidate_status_controller(
        profile_id="invalid-uuid",
        round_id="660e8400-e29b-41d4-a716-446655440000",
        input=mock_input,
        db=AsyncMock()
    )
    
    assert result['success'] is False
    assert result['status_code'] == 400


@pytest.mark.asyncio
async def test_update_candidate_status_general_exception():
    """Test update_candidate_status_controller when general exception occurs - covers lines 113-115"""
    with patch('app.controllers.shortlist_controller.ShortlistService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.update_candidate_status.side_effect = RuntimeError("Unexpected error")
        mock_service_class.return_value = mock_service
        
        mock_input = MagicMock()
        mock_input.new_result = "rejected"
        
        result = await update_candidate_status_controller(
            profile_id="550e8400-e29b-41d4-a716-446655440000",
            round_id="660e8400-e29b-41d4-a716-446655440000",
            input=mock_input,
            db=AsyncMock()
        )
        
        assert result['success'] is False
        assert result['status_code'] == 500
        assert 'Unable to update result' in result['message']
