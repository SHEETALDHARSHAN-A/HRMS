"""
Comprehensive tests for verify_otp, shortlist services and repositories
Targets: verify_otp_service.py, shortlist_service.py, shortlist_repository.py
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException, status, Response

from app.services.authentication_service.verify_otp_service import VerifyOtpService
from app.services.shortlist_service.shortlist_service import ShortlistService
from app.schemas.authentication_request import VerifyOTPRequest
from app.schemas.update_shortlist_request import UpdateShortlistRequest


# ============================================================================
# verify_otp_service.py Tests (97% -> 100%)
# Missing lines: 52, 62
# ============================================================================

@pytest.mark.asyncio
async def test_verify_otp_user_already_exists_signup():
    """Test verify_otp when signing up but user exists - covers line 52"""
    service = VerifyOtpService(AsyncMock(), AsyncMock())
    
    otp_data = json.dumps({
        "otp": "123456",
        "mode_of_login": "sign_up",  # Signup mode
        "email": "existing@test.com"
    })
    
    service.cache.hget.return_value = otp_data
    
    mock_request = VerifyOTPRequest(email="existing@test.com", otp="123456")
    mock_response = MagicMock(spec=Response)
    
    with patch('app.services.authentication_service.verify_otp_service.check_user_existence') as mock_check:
        mock_check.return_value = MagicMock()  # User exists
        
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_otp(mock_request, mock_response)
        
        assert exc_info.value.status_code == 409
        assert "User already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_otp_user_not_found_after_verification():
    """Test verify_otp when user is None after verification - covers line 62"""
    service = VerifyOtpService(AsyncMock(), AsyncMock())
    
    otp_data = json.dumps({
        "otp": "123456",
        "mode_of_login": "sign_in",  # Sign-in mode
        "email": "missing@test.com"
    })
    
    service.cache.hget.return_value = otp_data
    service.cache.hdel.return_value = True
    
    mock_request = VerifyOTPRequest(email="missing@test.com", otp="123456")
    mock_response = MagicMock(spec=Response)
    
    with patch('app.services.authentication_service.verify_otp_service.check_user_existence') as mock_check:
        mock_check.return_value = None  # User doesn't exist
        
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_otp(mock_request, mock_response)
        
        assert exc_info.value.status_code == 404
        assert "User not found after OTP verification" in exc_info.value.detail


# ============================================================================
# shortlist_service.py Tests (93% -> 100%)
# Missing lines: 112-114
# ============================================================================

@pytest.mark.asyncio
async def test_update_candidate_status_value_error():
    """Test update_candidate_status when ValueError is raised - covers lines 105-109"""
    service = ShortlistService(AsyncMock())
    
    mock_input = UpdateShortlistRequest(new_result="shortlist", reason="Good candidate")
    
    with patch('app.services.shortlist_service.shortlist_service.upsert_shortlist_result') as mock_upsert:
        mock_upsert.side_effect = ValueError("No shortlist entry found")
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_candidate_status("profile123", "round456", mock_input)
        
        assert exc_info.value.status_code == 404
        assert "No shortlist entry found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_candidate_status_http_exception_propagates():
    """Test update_candidate_status when HTTPException is raised - covers line 110-111"""
    service = ShortlistService(AsyncMock())
    
    mock_input = UpdateShortlistRequest(new_result="reject", reason="Not qualified")
    
    with patch('app.services.shortlist_service.shortlist_service.upsert_shortlist_result') as mock_upsert:
        mock_upsert.side_effect = HTTPException(status_code=403, detail="Forbidden")
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_candidate_status("profile123", "round456", mock_input)
        
        # HTTPException should propagate without wrapping
        assert exc_info.value.status_code == 403
        assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_candidate_status_general_exception():
    """Test update_candidate_status when general exception occurs - covers lines 112-117"""
    service = ShortlistService(AsyncMock())
    
    mock_input = UpdateShortlistRequest(new_result="under_review", reason="Needs review")
    
    with patch('app.services.shortlist_service.shortlist_service.upsert_shortlist_result') as mock_upsert:
        mock_upsert.side_effect = RuntimeError("Database connection lost")
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_candidate_status("profile123", "round456", mock_input)
        
        assert exc_info.value.status_code == 500
        assert "Unable to update result" in exc_info.value.detail


# ============================================================================
# shortlist_repository.py Tests (95% -> 100%)
# Missing lines: 99, 147-148
# ============================================================================

@pytest.mark.asyncio
async def test_get_round_candidates_with_result_filter():
    """Test get_round_candidates with result filter - covers line 99"""
    from app.db.repository.shortlist_repository import get_round_candidates
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result
    
    # Call with a specific result filter (not "all")
    candidates = await get_round_candidates(
        mock_db,
        job_id="job123",
        round_id="round456",
        result_filter="shortlist"  # Specific filter
    )
    
    assert candidates == []
    # Verify the filter was applied in the query
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_round_candidates_experience_extraction_error():
    """Test get_round_candidates when experience extraction fails - covers lines 147-148"""
    from app.db.repository.shortlist_repository import get_round_candidates
    
    # Mock row with malformed experience data
    mock_row = SimpleNamespace(
        profile_id="p1",
        candidate_name="Jane Doe",
        candidate_email="jane@test.com",
        resume_data={
            "experience": "invalid_type"  # Not a list, will cause exception
        },
        result="shortlist",
        overall_score=85,
        score_explanation="Good",
        reason="Qualified",
        potential_score=90,
        location_score=80,
        role_fit_score=88,
        skill_score=85,
        skill_score_explanation={"python": "Expert"},
        round_status="shortlisted",
        round_name="Technical Round"
    )
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_db.execute.return_value = mock_result
    
    candidates = await get_round_candidates(mock_db, "job1", "round1")
    
    # Should handle error gracefully and default to "Fresher"
    assert len(candidates) == 1
    assert candidates[0]["experience_level"] == "Fresher"


@pytest.mark.asyncio
async def test_get_round_candidates_empty_experience_list():
    """Test get_round_candidates with empty experience list"""
    from app.db.repository.shortlist_repository import get_round_candidates
    
    mock_row = SimpleNamespace(
        profile_id="p2",
        candidate_name="John Smith",
        candidate_email="john@test.com",
        resume_data={"experience": []},  # Empty list
        result="under_review",
        overall_score=75,
        score_explanation="Average",
        reason="Review needed",
        potential_score=80,
        location_score=70,
        role_fit_score=75,
        skill_score=75,
        skill_score_explanation={},
        round_status="under_review",
        round_name="Initial Round"
    )
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_db.execute.return_value = mock_result
    
    candidates = await get_round_candidates(mock_db, "job1", "round1")
    
    assert len(candidates) == 1
    assert candidates[0]["experience_level"] == "Fresher"


@pytest.mark.asyncio
async def test_get_round_candidates_with_years_experience():
    """Test get_round_candidates with valid years experience"""
    from app.db.repository.shortlist_repository import get_round_candidates
    
    mock_row = SimpleNamespace(
        profile_id="p3",
        candidate_name="Senior Dev",
        candidate_email="senior@test.com",
        resume_data={"experience": [{"years": 5, "company": "Tech Corp"}]},
        result="shortlist",
        overall_score=95,
        score_explanation="Excellent",
        reason="Top candidate",
        potential_score=95,
        location_score=90,
        role_fit_score=93,
        skill_score=92,
        skill_score_explanation={"leadership": "Strong"},
        round_status="shortlisted",
        round_name="Final Round"
    )
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_db.execute.return_value = mock_result
    
    candidates = await get_round_candidates(mock_db, "job1", "round1")
    
    assert len(candidates) == 1
    assert candidates[0]["experience_level"] == "5 Years Experience"
