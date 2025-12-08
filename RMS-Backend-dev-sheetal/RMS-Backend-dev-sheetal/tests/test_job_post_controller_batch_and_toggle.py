import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.utils.standard_response_utils import ResponseBuilder


@pytest.mark.asyncio
async def test_delete_job_posts_batch_invalid_ids(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Reader returns None for invalid id
    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return None

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})

    res = await jpc.delete_job_posts_batch_controller(['bad-id'], request=fake_request)
    assert res.get('success') is False
    assert res.get('status_code') == 400


@pytest.mark.asyncio
async def test_delete_job_posts_batch_unauthorized_ids(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Reader returns jobs owned by someone else
    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"job_id": job_id, "user_id": "other"}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})

    res = await jpc.delete_job_posts_batch_controller(['id1', 'id2'], request=fake_request)
    assert res.get('success') is False
    assert res.get('status_code') == 403


@pytest.mark.asyncio
async def test_delete_job_posts_batch_super_admin_service_forward(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # SUPER_ADMIN user
    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "admin", "sub": "admin", "role": "SUPER_ADMIN"})

    # Patch UpdateJobPost.delete_jobs_batch to return a dict result
    class FakeUpdate:
        def __init__(self, db):
            pass

        def delete_jobs_batch(self, job_ids):
            return {"success": True, "rows_affected": len(job_ids)}

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)

    res = await jpc.delete_job_posts_batch_controller(['a', 'b', 'c'], request=fake_request)
    # Controller should forward the dict
    assert isinstance(res, dict)
    assert res.get('success') is True


@pytest.mark.asyncio
async def test_toggle_job_status_repository_fallback_success(monkeypatch):
    import app.controllers.job_post_controller as jpc

    async def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    # Reader returns a job payload
    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"job_id": job_id, "created_by_user_id": "u1", "is_active": True}

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)

    # allow editing
    monkeypatch.setattr(jpc.JobPostPermissions, 'can_edit_job', staticmethod(lambda job, user: True))

    # Toggle service returns non-dict so repository fallback is used
    class FakeUpdate:
        def __init__(self, db):
            pass

        def toggle_status(self, job_id, is_active):
            return None

    monkeypatch.setattr(jpc, 'UpdateJobPost', FakeUpdate)

    # Patch repository setter to succeed
    async def fake_set_job_active_status(db, job_id=None, is_active=False):
        return True

    monkeypatch.setattr(jpc, 'set_job_active_status', fake_set_job_active_status)

    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "u1", "sub": "u1"})

    res = await jpc.toggle_job_status_controller('jid', True, request=fake_request)
    assert res.get('success') is True
    assert res.get('data') and res.get('data').get('job_details')
