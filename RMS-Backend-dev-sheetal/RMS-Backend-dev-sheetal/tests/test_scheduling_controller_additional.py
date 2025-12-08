import pytest
from types import SimpleNamespace
from fastapi import HTTPException, status
from app.controllers import scheduling_controller as sc


@pytest.mark.asyncio
async def test_scheduling_interview_controller_json_mapping_and_service_success(monkeypatch):
    class FakeRequest:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    class FakeService:
        def __init__(self, db=None):
            self.db = db

        async def schedule_candidate(self, interview_request):
            return {"status_code": 200, "data": {"ok": True}}

    monkeypatch.setattr(sc, "Scheduling", FakeService)
    req = FakeRequest({"custom_subject": "Hi", "custom_body": "World"})
    # Build a minimal SchedulingInterviewRequest-like object
    interview_request = SimpleNamespace(email_subject=None, email_body=None)
    res = await sc.scheduling_interview_controller(req, interview_request, db=None)
    assert isinstance(res, dict)
    assert res.get('status_code') == 200
    # Ensure mapping applied
    assert interview_request.email_subject == "Hi"
    assert interview_request.email_body == "World"


@pytest.mark.asyncio
async def test_scheduling_interview_controller_json_read_raises_and_http_exception(monkeypatch):
    class BadRequest:
        async def json(self):
            raise RuntimeError('bad json')

    class FakeServiceHTTP:
        def __init__(self, db=None):
            self.db = db

        async def schedule_candidate(self, interview_request):
            raise HTTPException(status_code=400, detail='bad')

    monkeypatch.setattr(sc, "Scheduling", FakeServiceHTTP)
    req = BadRequest()
    interview_request = SimpleNamespace(email_subject=None, email_body=None)
    res = await sc.scheduling_interview_controller(req, interview_request, db=None)
    assert isinstance(res, dict)
    assert res.get('status_code') == 400


@pytest.mark.asyncio
async def test_scheduling_interview_controller_service_error(monkeypatch):
    class BadService:
        def __init__(self, db=None):
            self.db = db

        async def schedule_candidate(self, interview_request):
            raise RuntimeError('boom')

    monkeypatch.setattr(sc, "Scheduling", BadService)
    req = SimpleNamespace()
    interview_request = SimpleNamespace(email_subject=None, email_body=None)
    res = await sc.scheduling_interview_controller(req, interview_request, db=None)
    assert isinstance(res, dict)
    assert res.get('status_code') == 500


@pytest.mark.asyncio
async def test_get_scheduled_interviews_controller_paths(monkeypatch):
    # success
    async def fake_get_scheduled_interviews(job_id, round_id, db):
        return []

    monkeypatch.setattr(sc, "get_scheduled_interviews", fake_get_scheduled_interviews)
    res = await sc.get_scheduled_interviews_controller(job_id='j', round_id='r', db=None)
    assert isinstance(res, dict)
    assert res.get('status_code') == 200

    # http exception
    async def fake_raise_http(job_id, round_id, db):
        raise HTTPException(status_code=403, detail='no')

    monkeypatch.setattr(sc, "get_scheduled_interviews", fake_raise_http)
    res2 = await sc.get_scheduled_interviews_controller(job_id='j', round_id='r', db=None)
    assert isinstance(res2, dict)
    assert res2.get('status_code') == 403

    # generic exception
    async def fake_raise(job_id, round_id, db):
        raise RuntimeError('boom')

    monkeypatch.setattr(sc, "get_scheduled_interviews", fake_raise)
    res3 = await sc.get_scheduled_interviews_controller(job_id='j', round_id='r', db=None)
    assert isinstance(res3, dict)
    assert res3.get('status_code') == 500
