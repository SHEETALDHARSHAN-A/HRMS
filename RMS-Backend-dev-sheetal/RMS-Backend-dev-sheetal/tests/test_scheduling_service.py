import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import date, time, datetime, timezone, timedelta
from fastapi import HTTPException, status

from app.services.scheduling_service.scheduling_service import Scheduling
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest
import app.services.scheduling_service.scheduling_service as service_mod


@pytest.mark.asyncio
async def test_schedule_candidate_conflict(monkeypatch):
    db = SimpleNamespace()
    s = Scheduling(db=db)
    # check_existing_schedules returns same list -> conflict
    monkeypatch.setattr(service_mod, 'check_existing_schedules', AsyncMock(return_value=['p1']))
    req = SchedulingInterviewRequest(
        job_id='job1', profile_id=['p1'], round_id='r1', interview_date=date.today(), interview_time=time(10, 0)
    )
    with pytest.raises(HTTPException) as excinfo:
        await s.schedule_candidate(req)
    assert excinfo.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_schedule_candidate_no_candidate_details(monkeypatch):
    db = SimpleNamespace()
    s = Scheduling(db=db)
    monkeypatch.setattr(service_mod, 'check_existing_schedules', AsyncMock(return_value=[]))
    monkeypatch.setattr(service_mod, 'get_candidate_details_for_scheduling', AsyncMock(return_value=[]))
    req = SchedulingInterviewRequest(
        job_id='job1', profile_id=['p2'], round_id='r1', interview_date=date.today(), interview_time=time(10, 0)
    )
    with pytest.raises(HTTPException) as excinfo:
        await s.schedule_candidate(req)
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_schedule_candidate_all_emails_failed(monkeypatch):
    db = SimpleNamespace()
    s = Scheduling(db=db)
    monkeypatch.setattr(service_mod, 'check_existing_schedules', AsyncMock(return_value=[]))
    monkeypatch.setattr(service_mod, 'get_candidate_details_for_scheduling', AsyncMock(return_value=[{'user_id': 'p3', 'email': 'a@example.com', 'first_name': 'A', 'last_name': 'B'}]))
    monkeypatch.setattr(service_mod, 'get_job_title_by_id', AsyncMock(return_value='J Title'))
    monkeypatch.setattr(service_mod, 'get_round_name_by_id', AsyncMock(return_value={'round_name': 'Round 1'}))
    monkeypatch.setattr(service_mod, 'get_next_round_details', AsyncMock(return_value={'round_name': 'Final'}))
    # fail send email
    monkeypatch.setattr(service_mod, 'send_interview_invite_email_async', AsyncMock(return_value=False))
    future_dt = datetime.now(timezone.utc) + timedelta(days=2)
    req = SchedulingInterviewRequest(
        job_id='job1', profile_id=['p3'], round_id='r1', interview_date=future_dt.date(), interview_time=time(10, 0)
    )
    with pytest.raises(HTTPException) as excinfo:
        await s.schedule_candidate(req)
    assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_schedule_candidate_success(monkeypatch):
    db = SimpleNamespace()
    s = Scheduling(db=db)
    monkeypatch.setattr(service_mod, 'check_existing_schedules', AsyncMock(return_value=[]))
    monkeypatch.setattr(service_mod, 'get_candidate_details_for_scheduling', AsyncMock(return_value=[{'user_id': 'p4', 'email': 'a@example.com', 'first_name': 'A', 'last_name': 'B'}]))
    monkeypatch.setattr(service_mod, 'get_job_title_by_id', AsyncMock(return_value='J Title'))
    monkeypatch.setattr(service_mod, 'get_round_name_by_id', AsyncMock(return_value={'round_name': 'Round 1'}))
    monkeypatch.setattr(service_mod, 'get_next_round_details', AsyncMock(return_value={'round_name': 'Final'}))
    monkeypatch.setattr(service_mod, 'send_interview_invite_email_async', AsyncMock(return_value=True))
    monkeypatch.setattr(service_mod, 'create_schedules_batch', AsyncMock(return_value=['id1']))
    # Also patch EmailTemplateService to avoid rendering complexity
    monkeypatch.setattr(service_mod.EmailTemplateService, 'get_template', AsyncMock(return_value={'subject_template': 'S','body_template_html': '<p>B</p>'}))
    monkeypatch.setattr(service_mod.EmailTemplateService, 'get_template_preview_content', AsyncMock(return_value=('Sout', '<p>Bout</p>')))

    future_dt = datetime.now(timezone.utc) + timedelta(days=2)
    req = SchedulingInterviewRequest(
        job_id='job2', profile_id=['p4'], round_id='r1', interview_date=future_dt.date(), interview_time=time(10, 0)
    )
    res = await s.schedule_candidate(req)
    assert res['data']['scheduled_count'] == 1
