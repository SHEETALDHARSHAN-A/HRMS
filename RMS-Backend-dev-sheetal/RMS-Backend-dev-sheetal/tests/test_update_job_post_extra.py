import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from app.services.job_post.update_jd.update_job_post import UpdateJobPost


class StubJD:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._dump = kwargs
        self.model_fields_set = set(kwargs.keys())

    def __getattr__(self, name):
        return None

    def model_dump(self, exclude_unset=False, exclude=None):
        d = dict(self._dump)
        if exclude:
            for k in exclude:
                d.pop(k, None)
        return d


@pytest.mark.asyncio
async def test_agent_screening_inherits_fit_scores(monkeypatch):
    # Ensure role_fit/potential_fit/location_fit are propagated to agent config for screening rounds
    jd = StubJD(job_title='X', minimum_experience=0, maximum_experience=0, skills_required=[],
                role_fit=20, potential_fit=15, location_fit=10,
                agent_configs=[{"roundName": "Screen Initial", "interview_time_min": 5, "interview_time_max": 15}])

    called = {}

    async def fake_update_or_create_job_details(db, job_id, job_data, **kwargs):
        called['agent_configs'] = kwargs.get('agent_configs_data')
        return SimpleNamespace(job_id=job_id, user_id=job_data.get('user_id'))

    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.update_or_create_job_details', fake_update_or_create_job_details)
    svc = UpdateJobPost(db=None)
    res = await svc.update_job_post(jd, job_id=None, creator_id='u1')
    assert res['success'] is True
    ac = called['agent_configs'][0]
    assert 'role_fit' in ac and ac['role_fit'] == 20
    assert 'potential_fit' in ac and ac['potential_fit'] == 15
    assert 'location_fit' in ac and ac['location_fit'] == 10


@pytest.mark.asyncio
async def test_agent_time_bounds_non_int_raise(monkeypatch):
    # Provide agent mode with non-int tmin to validate HTTPException
    jd = StubJD(job_title='X', minimum_experience=0, maximum_experience=0, skills_required=[],
                agent_configs=[{"interview_mode": "agent", "interview_time_min": "notint", "interview_time_max": "10"}])

    svc = UpdateJobPost(db=None)
    res = await svc.update_job_post(jd, job_id=None, creator_id='u1')
    assert res['success'] is False
    assert res['status_code'] == 422
