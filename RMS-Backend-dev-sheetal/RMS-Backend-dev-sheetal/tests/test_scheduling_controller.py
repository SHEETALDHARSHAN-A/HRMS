import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException, status
from datetime import date, time

from app.controllers import scheduling_controller as ctrl
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest
from app.services.scheduling_service.scheduling_service import Scheduling


class FakeRequest:
    def __init__(self, payload=None):
        self._payload = payload or {}

    async def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_scheduling_interview_controller_success(monkeypatch, fake_db):
    # Arrange: create a request object and a SchedulingInterviewRequest model
    req_payload = {
        'custom_subject': 'Hello {{CANDIDATE_NAME}}',
        'custom_body': '<p>{{CANDIDATE_NAME}}</p>'
    }
    fake_request = FakeRequest(req_payload)

    interview_request = SchedulingInterviewRequest(
        job_id='00000000-0000-0000-0000-000000000001',
        profile_id=['00000000-0000-0000-0000-000000000002'],
        round_id='00000000-0000-0000-0000-000000000003',
        interview_date=date.today(),
        interview_time=time(10, 0),
    )

    ret = {"message": "Interview scheduling completed.", "data": {"scheduled_count": 1}, "status_code": status.HTTP_200_OK}
    mock_sched = AsyncMock(return_value=ret)
    monkeypatch.setattr(Scheduling, 'schedule_candidate', mock_sched)

    # Act
    resp = await ctrl.scheduling_interview_controller(fake_request, interview_request, fake_db)

    # Assert
    assert resp['message'] == "Interview scheduling completed."
    assert resp['data']['scheduled_count'] == 1
    # Validate that the Scheduling service was invoked with our model
    assert mock_sched.await_count == 1
    called_req = mock_sched.call_args[0][0]
    assert called_req.email_subject == req_payload['custom_subject']


@pytest.mark.asyncio
async def test_scheduling_interview_controller_service_http_exception(monkeypatch, fake_db):
    interview_request = SchedulingInterviewRequest(
        job_id='00000000-0000-0000-0000-000000000004',
        profile_id=['00000000-0000-0000-0000-000000000005'],
        round_id='00000000-0000-0000-0000-000000000006',
        interview_date=date.today(),
        interview_time=time(10, 0),
    )

    exc = HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already scheduled")
    mock_sched = AsyncMock(side_effect=exc)
    monkeypatch.setattr(Scheduling, 'schedule_candidate', mock_sched)

    resp = await ctrl.scheduling_interview_controller(FakeRequest(), interview_request, fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_get_scheduled_interviews_controller_success(monkeypatch, fake_db):
    sample_list = [{'id': '1'}]
    monkeypatch.setattr(ctrl, 'get_scheduled_interviews', AsyncMock(return_value=sample_list))

    resp = await ctrl.get_scheduled_interviews_controller("jid", "rid", fake_db)
    assert resp['success'] is True
    assert resp['data']['interviews'] == sample_list


@pytest.mark.asyncio
async def test_get_scheduled_interviews_controller_error(monkeypatch, fake_db):
    monkeypatch.setattr(ctrl, 'get_scheduled_interviews', AsyncMock(side_effect=Exception('fail')))
    resp = await ctrl.get_scheduled_interviews_controller("jid", "rid", fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_500_INTERNAL_SERVER_ERROR
