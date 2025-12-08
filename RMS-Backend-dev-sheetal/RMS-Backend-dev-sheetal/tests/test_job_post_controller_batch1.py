import pytest
from types import SimpleNamespace
import inspect

import app.controllers.job_post_controller as jpc


# Helper: async generator to replace get_db dependency
async def fake_get_db():
    yield "FAKE_DB"


class DummyRequest:
    def __init__(self, user=None):
        self.state = SimpleNamespace(user=user)


@pytest.mark.asyncio
async def test_get_job_by_id_invalid_uuid():
    resp = await jpc.get_job_by_id_controller('not-a-uuid', request=None)
    assert isinstance(resp, dict)
    assert resp.get('success') is False
    assert resp.get('status_code') == 400


@pytest.mark.asyncio
async def test_get_job_by_id_happy_path(monkeypatch):
    # Arrange: patch get_db and GetJobPost to return a job payload
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeGetJob:
        def __init__(self, db):
            self.db = db

        def fetch_full_job_details(self, job_id):
            return {"job_id": job_id, "user_id": "user-1", "job_title": "Title"}

    monkeypatch.setattr(jpc, 'GetJobPost', FakeGetJob)
    # Ensure permission check returns True
    monkeypatch.setattr(jpc.JobPostPermissions, 'can_edit_job', lambda job, user: True)

    req = DummyRequest(user={"user_id": "user-1"})
    result = await jpc.get_job_by_id_controller('11111111-1111-1111-1111-111111111111', request=req)

    assert result.get('success') is True
    data = result.get('data')
    assert 'job' in data
    # controller removes internal user_id
    assert 'user_id' not in data['job']


@pytest.mark.asyncio
async def test_get_public_job_by_id_inactive_and_active(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id=None):
            return {"job_id": job_id, "is_active": False}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    # Inactive -> 404
    res = await jpc.get_public_job_by_id_controller('1111')
    assert res.get('success') is False
    assert res.get('status_code') == 404

    # Active -> success
    class ActiveReader(FakeReader):
        def get_job(self, job_id=None):
            return {"job_id": job_id, "is_active": True, "job_title": "T", "job_location": "L", "work_from_home": True, "skills_required": [{"skill":"s1"}]}

    monkeypatch.setattr(jpc, 'JobPostReader', ActiveReader)
    res2 = await jpc.get_public_job_by_id_controller('2222')
    assert res2.get('success') is True
    assert 'job' in res2.get('data')


@pytest.mark.asyncio
async def test_get_active_jobs_controller(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def list_active(self):
            return [{"job_id": "j1"}, {"job_id": "j2"}]

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    res = await jpc.get_active_jobs_controller()
    assert res.get('success') is True
    assert isinstance(res.get('data', {}).get('jobs'), list)
    assert len(res.get('data', {}).get('jobs')) == 2


@pytest.mark.asyncio
async def test_toggle_job_status_permission_denied(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "owner-1", "is_active": True}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    # Permission check returns False
    monkeypatch.setattr(jpc.JobPostPermissions, 'can_edit_job', lambda job, user: False)

    req = DummyRequest(user={"user_id": "other-1"})
    res = await jpc.toggle_job_status_controller('jid', True, request=req)
    assert res.get('success') is False
    assert res.get('status_code') == 403
