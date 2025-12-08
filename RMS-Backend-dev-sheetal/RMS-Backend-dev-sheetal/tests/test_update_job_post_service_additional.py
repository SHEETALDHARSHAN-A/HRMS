import pytest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.services.job_post.update_jd.update_job_post import UpdateJobPost
from app.schemas.update_jd_request import UpdateJdRequest


class StubJD:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        # Allow model_dump() calls
        self._dump = kwargs
        self.model_fields_set = set(kwargs.keys())

    def __getattr__(self, name):
        # If a test doesn't provide some optional attributes, return None
        # to match the behavior of missing optional fields in Pydantic models
        return None

    def model_dump(self, exclude_unset=False, exclude=None):
        d = dict(self._dump)
        # Respect exclude
        if exclude:
            for k in exclude:
                d.pop(k, None)
        return d


@pytest.mark.asyncio
async def test_minimum_experience_validation_raises():
    svc = UpdateJobPost(db=None)
    # Create a stub certifying job_details with min>max
    jd = StubJD(minimum_experience=5, maximum_experience=3, job_title="x")
    res = await svc.update_job_post(jd)
    assert res.get('success') is False
    assert res.get('status_code') == 422


@pytest.mark.asyncio
async def test_agent_config_time_bounds_requirements_raise():
    svc = UpdateJobPost(db=None)
    # agent mode but missing time bounds
    jd = StubJD(job_title="x", minimum_experience=1, maximum_experience=5, skills_required=[], agent_configs=[{"interview_mode":"agent"}])
    res = await svc.update_job_post(jd)
    assert res.get('success') is False
    assert res.get('status_code') == 422


@pytest.mark.asyncio
async def test_offline_interviewer_required_raises():
    svc = UpdateJobPost(db=None)
    jd = StubJD(job_title="x", minimum_experience=1, maximum_experience=2, skills_required=[], agent_configs=[{"interview_mode":"offline"}])
    res = await svc.update_job_post(jd)
    assert res.get('success') is False
    assert res.get('status_code') == 422


@pytest.mark.asyncio
async def test_update_merges_existing_job_and_calls_repo(monkeypatch):
    # Build a StubJD with some fields
    jd = StubJD(job_title="x", minimum_experience=1, maximum_experience=2, skills_required=[])
    svc = UpdateJobPost(db=MagicMock())
    # Prepare existing job from repo.get_job_details_by_id       
    existing_job = SimpleNamespace(id=str(uuid.uuid4()), job_title="old", user_id="u1")
    # Monkeypatch the repo functions to inspect called args
    called = {}

    async def fake_get(job_db, job_id):
        return existing_job

    async def fake_update(db, job_id, job_data, skills_data=None, description_data=None, location_data=None, rounds_data=None, agent_configs_data=None):
        called['job_id'] = job_id
        called['job_data'] = job_data
        return existing_job

    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.get_job_details_by_id', fake_get)
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.update_or_create_job_details', fake_update)
    # Also patch serializer to return a dict
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.serialize_job_details', lambda job: {"id": job.id})

    res = await svc.update_job_post(jd, job_id=str(existing_job.id))
    assert called['job_id'] == str(existing_job.id)
    assert isinstance(called['job_data'], dict)


@pytest.mark.asyncio
async def test_create_calls_repo_and_returns_serialized(monkeypatch):
    jd = StubJD(job_title="create", minimum_experience=0, maximum_experience=0, skills_required=[])
    svc = UpdateJobPost(db=MagicMock())
    created_job = MagicMock()
    async def fake_create(db, job_id, job_data, skills_data=None, description_data=None, location_data=None, rounds_data=None, agent_configs_data=None):
        return created_job

    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.update_or_create_job_details', fake_create)
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.serialize_job_details', lambda job: {"id": 'abc'})
    res = await svc.update_job_post(jd, job_id=None, creator_id='u1')
    assert res.get('success') is True
    assert res.get('job_details', {}).get('id') == 'abc'
