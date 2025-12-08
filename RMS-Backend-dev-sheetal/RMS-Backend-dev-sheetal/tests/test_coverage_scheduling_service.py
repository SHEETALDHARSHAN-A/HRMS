import pytest
from datetime import datetime, timezone, timedelta, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.services.scheduling_service.scheduling_service import Scheduling
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest

@pytest.mark.asyncio
async def test_schedule_candidate_past_date_raises(fake_db):
    svc = Scheduling(fake_db)
    
    # Date in the past
    past = datetime.now(timezone.utc) - timedelta(days=1)
    req = SchedulingInterviewRequest(
        job_id="j1", profile_id=["p1"], round_id="r1",
        interview_date=past.date(), interview_time=time(10,0)
    )
    
    # Mock check_existing_schedules to return empty
    with patch("app.services.scheduling_service.scheduling_service.check_existing_schedules", AsyncMock(return_value=[])):
        # Mock candidate details
        with patch("app.services.scheduling_service.scheduling_service.get_candidate_details_for_scheduling", AsyncMock(return_value=[{"user_id": "p1"}])):
             with pytest.raises(HTTPException) as exc:
                 await svc.schedule_candidate(req)
             assert exc.value.status_code == 422
             assert "Invalid date" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_schedule_candidate_too_far_future_raises(fake_db):
    svc = Scheduling(fake_db)
    future = datetime.now(timezone.utc) + timedelta(days=65)
    req = SchedulingInterviewRequest(
        job_id="j1", profile_id=["p1"], round_id="r1",
        interview_date=future.date(), interview_time=time(10,0)
    )
    with patch("app.services.scheduling_service.scheduling_service.check_existing_schedules", AsyncMock(return_value=[])):
        with patch("app.services.scheduling_service.scheduling_service.get_candidate_details_for_scheduling", AsyncMock(return_value=[{"user_id": "p1"}])):
             with pytest.raises(HTTPException) as exc:
                 await svc.schedule_candidate(req)
             assert exc.value.status_code == 422
             assert "Invalid date" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_schedule_candidate_email_failure_handling(fake_db):
    svc = Scheduling(fake_db)
    # Use tomorrow's date to avoid flakiness caused by timezone conversions
    today = datetime.now(timezone.utc) + timedelta(days=1)
    
    req = SchedulingInterviewRequest(
        job_id="j1", profile_id=["p1"], round_id="r1",
        interview_date=today.date(), interview_time=time(10,0) # safe future time
    )

    with patch("app.services.scheduling_service.scheduling_service.check_existing_schedules", AsyncMock(return_value=[])):
        with patch("app.services.scheduling_service.scheduling_service.get_candidate_details_for_scheduling", 
                   AsyncMock(return_value=[{"user_id": "p1", "email": "a@b.com"}])):
            with patch("app.services.scheduling_service.scheduling_service.get_job_title_by_id", AsyncMock(return_value="Job")):
                 # Mock email failure
                 with patch("app.services.scheduling_service.scheduling_service.send_interview_invite_email_async", AsyncMock(return_value=False)):
                     # If email sending fails for all candidates, scheduling should fail
                     with pytest.raises(HTTPException) as exc:
                         await svc.schedule_candidate(req)
                     assert exc.value.status_code == 500
                     assert "Scheduling failed for all candidates" in str(exc.value.detail)