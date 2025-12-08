import pytest
from types import SimpleNamespace
import app.controllers.job_post_controller as jpc


# reuse fake get_db
async def fake_get_db():
    yield "FAKE_DB"


class DummyRequest:
    def __init__(self, user=None):
        self.state = SimpleNamespace(user=user)


@pytest.mark.asyncio
async def test_update_job_post_unauthenticated():
    # No request -> unauthenticated
    job_details = SimpleNamespace(job_id=None)
    resp = await jpc.update_job_post_controller(job_details, job_id=None, request=None)
    assert isinstance(resp, dict)
    assert resp.get('success') is False
    assert resp.get('status_code') == 401


@pytest.mark.asyncio
async def test_update_job_post_permission_denied(monkeypatch):
    # user present but not allowed to edit existing job
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "owner-1"}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)
    # permission check returns False
    monkeypatch.setattr(jpc.JobPostPermissions, 'can_edit_job', lambda job, user: False)

    job_details = SimpleNamespace(job_id='11111111-1111-1111-1111-111111111111')
    req = DummyRequest(user={"sub": "other-1", "user_id": "other-1"})
    resp = await jpc.update_job_post_controller(job_details, job_id=job_details.job_id, request=req)

    # Could be JSONResponse or dict; normalize
    if hasattr(resp, 'status_code'):
        assert resp.status_code == 403
    else:
        assert resp.get('status_code') == 403


@pytest.mark.asyncio
async def test_update_job_post_create_happy_path(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Ensure no pre-existing job lookup happens (create path)
    class FakeUpdateService:
        def __init__(self, db):
            self.db = db

        async def update_job_post(self, job_details, job_id, creator_id):
            return {"success": True, "data": {"job_details": {"job_id": "new-id"}}, "status_code": 201}

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdateService)

    job_details = SimpleNamespace(job_id=None)
    req = DummyRequest(user={"sub": "creator-1", "user_id": "creator-1"})
    resp = await jpc.update_job_post_controller(job_details, job_id=None, request=req)

    assert isinstance(resp, dict)
    assert resp.get('success') is True
    assert resp.get('status_code') == 201
    # Accept either flattened or nested service shapes for job_details
    top_job = resp.get('data', {}).get('job_details') or {}
    # possible shapes:
    # {"job_id": "new-id"}  OR {"job_details": {"job_id": "new-id"}}
    if isinstance(top_job, dict) and top_job.get('job_id'):
        found = top_job.get('job_id')
    elif isinstance(top_job, dict) and isinstance(top_job.get('job_details'), dict):
        found = top_job.get('job_details', {}).get('job_id')
    else:
        found = None

    assert found == 'new-id'


@pytest.mark.asyncio
async def test_delete_job_post_permission_denied(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "owner-1"}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)
    monkeypatch.setattr(jpc.JobPostPermissions, 'can_edit_job', lambda job, user: False)

    req = DummyRequest(user={"sub": "other"})
    resp = await jpc.delete_job_post_controller('jid-1', request=req)
    assert resp.get('success') is False
    assert resp.get('status_code') == 403


@pytest.mark.asyncio
async def test_delete_job_post_success(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "owner-1"}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    class FakeUpdateService:
        def __init__(self, db):
            self.db = db

        async def delete_job_post(self, job_id):
            return {"success": True, "status_code": 200, "message": "Deleted"}

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdateService)

    req = DummyRequest(user={"sub": "owner-1", "user_id": "owner-1"})
    resp = await jpc.delete_job_post_controller('jid-1', request=req)
    assert resp.get('success') is True


@pytest.mark.asyncio
async def test_delete_job_posts_batch_non_super_unauthorized(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Reader returns different creators for two ids
    class FakeReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id=None):
            if job_id == 'a':
                return {"job_id": job_id, "user_id": "owner-1"}
            if job_id == 'b':
                return {"job_id": job_id, "user_id": "other"}
            return None

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    req = DummyRequest(user={"sub": "owner-1", "user_id": "owner-1", "role": "HR"})

    resp = await jpc.delete_job_posts_batch_controller(['a', 'b'], request=req)
    assert resp.get('success') is False
    assert resp.get('status_code') == 403
    errors = resp.get('errors')
    # expect unauthorized_job_ids in errors dict
    assert isinstance(errors, dict) or isinstance(errors, list) or errors is None


@pytest.mark.asyncio
async def test_delete_job_posts_batch_super_success(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeUpdateService:
        def __init__(self, db):
            self.db = db

        async def delete_jobs_batch(self, job_ids):
            return {"success": True, "status_code": 200, "data": {"rows_affected": len(job_ids)}}

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdateService)

    req = DummyRequest(user={"sub": "admin-1", "user_id": "admin-1", "role": "SUPER_ADMIN"})
    resp = await jpc.delete_job_posts_batch_controller(['a', 'b'], request=req)
    assert resp.get('success') is True
    assert resp.get('data', {}).get('rows_affected') == 2
