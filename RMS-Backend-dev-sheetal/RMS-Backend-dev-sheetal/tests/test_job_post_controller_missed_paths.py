import pytest
import types
import inspect
from fastapi import HTTPException, status
from types import SimpleNamespace

from app.controllers import job_post_controller as jpc
from app.utils.standard_response_utils import ResponseBuilder


# Utility: async generator that yields a dummy DB object
async def fake_get_db():
    yield object()


@pytest.mark.asyncio
async def test_update_job_post_controller_http_exception(monkeypatch):
    """UpdateJobPost.update_job_post raises HTTPException -> controller should return JSONResponse (error)."""
    # monkeypatch get_db to yield a db object
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Fake UpdateJobPost whose update_job_post raises HTTPException
    class FakeUpdateService:
        def __init__(self, db):
            self.db = db

        async def update_job_post(self, job_details=None, job_id=None, creator_id=None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad update")

    monkeypatch.setattr(jpc, "UpdateJobPost", FakeUpdateService)

    # Minimal job details required by controller's usage; provide simple namespace w/model_dump
    job_details = SimpleNamespace(model_dump=lambda: {"job_id": "jjj"})

    # Also ensure JobPostReader.get_job returns a job the user owns so we don't hit 404
    class FakeJobReader:
        def __init__(self, db):
            self.db = db

        async def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "u-1", "created_by_user_id": "u-1"}

    monkeypatch.setattr(jpc, "JobPostReader", FakeJobReader)

    # Provide a request with authenticated user info to avoid the 401 early return
    request = SimpleNamespace(state=SimpleNamespace(user={"sub": "u-1", "user_id": "u-1"}))
    res = await jpc.update_job_post_controller(job_details=job_details, job_id="jjj", request=request)

    # Should be a JSONResponse or dict-like error; ResponseBuilder.error returns dict
    assert isinstance(res, dict) or hasattr(res, 'status_code')
    if isinstance(res, dict):
        assert res.get('status_code') == status.HTTP_400_BAD_REQUEST
    else:
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_my_jobs_controller_no_user_id(monkeypatch):
    """When current_user has no user_id field, returns 401 error payload."""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Build fake request with state.user lacking user_id
    request = SimpleNamespace(state=SimpleNamespace(user={}))

    res = await jpc.get_my_jobs_controller(request)

    assert isinstance(res, dict)
    assert res.get('status_code') == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_my_agent_jobs_controller_unauth_and_no_user_id(monkeypatch):
    """Ex 1: no request.user -> 401; Ex 2: user exists but no user_id -> 401"""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Case 1: request has no state -> acts as unauthenticated
    request_none = SimpleNamespace()  # no 'state'
    res = await jpc.get_my_agent_jobs_controller(request_none)
    assert isinstance(res, dict)
    assert res.get('status_code') == status.HTTP_401_UNAUTHORIZED

    # Case 2: request.state.user present but no user_id
    request = SimpleNamespace(state=SimpleNamespace(user={}))
    res2 = await jpc.get_my_agent_jobs_controller(request)
    assert isinstance(res2, dict)
    assert res2.get('status_code') == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_my_agent_jobs_controller_exception_path(monkeypatch):
    """Simulate get_agent_jobs_by_user_id raising -> controller should route to _handle_controller_exception.
    We'll monkeypatch the repository function to raise.
    """
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Provide a valid user
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1"}))

    async def bad_get_agent_jobs(db, user_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(jpc, "get_agent_jobs_by_user_id", bad_get_agent_jobs)

    res = await jpc.get_my_agent_jobs_controller(request)
    # Controller returns a JSONResponse via _handle_controller_exception
    # or a dict; accept both and check for 500
    assert isinstance(res, dict) or hasattr(res, 'status_code')
    if isinstance(res, dict):
        assert res.get('status_code') == 500
    else:
        assert res.status_code == 500


@pytest.mark.asyncio
async def test_get_job_by_id_controller_fallback_reader(monkeypatch):
    """Make GetJobPost import wrapper raise in constructor so the fallback reader.get_job path is used.
    Ensure the job_candidate await path (line 517) runs by returning an awaitable from reader.get_job.
    """
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Make GetJobPost __init__ raise
    class BadImportedGetJobDetails:
        def __init__(self, db):
            raise Exception('import fail')

    monkeypatch.setattr(jpc, "_ImportedGetJobDetails", BadImportedGetJobDetails, raising=False)

    # Make JobPostReader.get_job be an async function that returns a dict
    class FakeReader:
        def __init__(self, db):
            self.db = db

        async def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "u-1", "job_title": 't', 'is_active': True}

    monkeypatch.setattr(jpc, "JobPostReader", FakeReader)

    # Call with a valid uuid-like string
    res = await jpc.get_job_by_id_controller(job_id="11111111-1111-1111-1111-111111111111", request=SimpleNamespace())
    assert isinstance(res, dict)
    assert res.get('message') == "Fetched job." or res.get('data')


@pytest.mark.asyncio
async def test_get_public_job_by_id_controller_not_found_and_exception(monkeypatch):
    """Cover job not found (552) and exception path (579-581) in public job controller.
    """
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Job not found: reader returns None
    class FakeReaderNone:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            return None

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderNone)

    res = await jpc.get_public_job_by_id_controller(job_id='abc')
    assert isinstance(res, dict)
    assert res.get('status_code') == 404

    # Exception path: reader raises
    class FakeReaderEx:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            raise RuntimeError('boom')

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderEx)

    res2 = await jpc.get_public_job_by_id_controller(job_id='abc')
    assert isinstance(res2, dict)
    assert res2.get('status_code') == 500


@pytest.mark.asyncio
async def test_toggle_job_status_controller_errors_and_fallback(monkeypatch):
    """Cover job not found, set_job_active_status False, and not found after update.
    """
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # 1) job not found -> JobPostReader returns None
    class FakeReaderNone:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            return None

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderNone)

    res = await jpc.toggle_job_status_controller(job_id='abc', is_active=True, request=SimpleNamespace())
    assert isinstance(res, dict)
    assert res.get('status_code') == 404

    # 2) fallback updated False -> ensure the job exists (to not hit 404) and set_job_active_status returns False
    class FakeReaderFound:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "u-1", "created_by_user_id": "u-1", "is_active": False}

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderFound)

    async def fake_set_job_active_status(db, job_id, is_active):
        return False

    monkeypatch.setattr(jpc, "set_job_active_status", fake_set_job_active_status)

    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1", "sub": "u-1"}))
    res2 = await jpc.toggle_job_status_controller(job_id='abc', is_active=True, request=request)
    assert isinstance(res2, dict)
    assert res2.get('status_code') == 400

    # 3) job not found after update -> set_job_active_status True but get_job returns None after update
    async def fake_true(db, job_id, is_active):
        return True

    monkeypatch.setattr(jpc, "set_job_active_status", fake_true)
    # Ensure UpdateJobPost.toggle_status doesn't return a payload (so controller falls back to repo)
    class FakeUpdateServiceNone:
        def __init__(self, db):
            pass

        async def toggle_status(self, job_id=None, is_active=None):
            return None

    monkeypatch.setattr(jpc, "UpdateJobPost", FakeUpdateServiceNone)
    # Use a sequence reader: returns job first, and None on second fetch
    class FakeReaderSequence:
        def __init__(self, db):
            self.calls = 0

        async def get_job(self, job_id=None):
            self.calls += 1
            if self.calls == 1:
                return {"job_id": job_id, "user_id": "u-1", "created_by_user_id": "u-1", "is_active": False}
            return None

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderSequence)
    res3 = await jpc.toggle_job_status_controller(job_id='abc', is_active=True, request=request)
    assert isinstance(res3, dict)
    assert res3.get('status_code') == 404


@pytest.mark.asyncio
async def test_delete_job_post_controller_not_found(monkeypatch):
    """Delete job post returns 404 when job not found."""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    class FakeReaderNone:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            return None

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderNone)

    res = await jpc.delete_job_post_controller(job_id='test', request=SimpleNamespace(state=SimpleNamespace(user={"user_id":"u-1"})))
    assert isinstance(res, dict)
    assert res.get('status_code') == 404


@pytest.mark.asyncio
async def test_get_analyze_jd_service_invoked(monkeypatch):
    """Ensure get_analyze_jd_service return line is covered and controller uses it."""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    class FakeAnalyzer:
        async def analyze_job_details(self, job_details=None):
            return {"ok": True}

    # Patch get_analyze_jd_service to return our fake
    monkeypatch.setattr(jpc, "get_analyze_jd_service", lambda: FakeAnalyzer())

    # Build a minimal AnalyzeJdRequest-like object: a SimpleNamespace with required fields or use SimpleNamespace
    job_details = SimpleNamespace(model_dump=lambda: {"job_title": "test"})
    res = await jpc.analyze_job_details_controller(job_details)
    assert isinstance(res, dict)
    assert res.get('status_code') == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_my_jobs_controller_exception_path_reader_raises(monkeypatch):
    """list_all raising should trigger the controller exception path (500)."""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1", "sub": "u-1"}))

    class ReaderRaises:
        def __init__(self, db):
            pass

        async def list_all(self):
            raise RuntimeError('boom')

    monkeypatch.setattr(jpc, "JobPostReader", ReaderRaises)
    res = await jpc.get_my_jobs_controller(request)
    assert isinstance(res, dict) or hasattr(res, 'status_code')
    if isinstance(res, dict):
        assert res.get('status_code') == 500
    else:
        assert res.status_code == 500


@pytest.mark.asyncio
async def test_get_job_by_id_controller_fallback_to_reader(monkeypatch):
    """Force GetJobPost.fetch_full_job_details to raise and ensure reader fallback path (await assignment) is hit."""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)
    # Force GetJobPost.fetch_full_job_details to raise
    class BadGetJobPost:
        def __init__(self, db):
            self.db = db

        def fetch_full_job_details(self, job_id):
            raise RuntimeError('boom in service')

    monkeypatch.setattr(jpc, "GetJobPost", BadGetJobPost)

    class FakeReaderAwait:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "u-1", "created_by_user_id": "u-1", "is_active": True}

    monkeypatch.setattr(jpc, "JobPostReader", FakeReaderAwait)
    res = await jpc.get_job_by_id_controller(job_id='11111111-1111-1111-1111-111111111111', request=SimpleNamespace())
    assert isinstance(res, dict)
    assert res.get('status_code') == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_toggle_job_status_controller_fallback_to_repo_updated_false(monkeypatch):
    """Direct test for fallback set_job_active_status returning False (400)."""
    monkeypatch.setattr(jpc, "get_db", fake_get_db)
    # Ensure permission check passes
    monkeypatch.setattr(jpc.JobPostPermissions, "can_edit_job", lambda job, cur: True)

    class FakeReader:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            return {"job_id": job_id, "user_id": "u-1", "created_by_user_id": "u-1", "is_active": False}

    monkeypatch.setattr(jpc, "JobPostReader", FakeReader)

    # Ensure UpdateJobPost.toggle_status returns None so controller falls back to repo
    class FakeUpdateNoResult:
        def __init__(self, db):
            pass

        async def toggle_status(self, job_id=None, is_active=None):
            return None

    monkeypatch.setattr(jpc, "UpdateJobPost", FakeUpdateNoResult)

    async def fake_set_job_active_status_false(db, job_id, is_active):
        return False

    monkeypatch.setattr(jpc, "set_job_active_status", fake_set_job_active_status_false)
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u-1", "sub": "u-1"}))
    res = await jpc.toggle_job_status_controller(job_id='abc', is_active=True, request=request)
    assert isinstance(res, dict) or hasattr(res, 'status_code')
    if isinstance(res, dict):
        assert res.get('status_code') == 400
    else:
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_delete_job_posts_batch_controller_paths(monkeypatch):
    """Cover missing user info, job lookup raising in loop and service.delete_jobs_batch raising fallback to hard_delete_jobs_batch, and exception for hard_delete_jobs_batch failing.
    """
    monkeypatch.setattr(jpc, "get_db", fake_get_db)

    # Case 1: request missing state.user -> unauthorized
    request = SimpleNamespace()
    res = await jpc.delete_job_posts_batch_controller(job_ids=['a','b'], request=request)
    assert isinstance(res, dict)
    assert res.get('status_code') == status.HTTP_401_UNAUTHORIZED

    # Case 2: job lookup raises for a job (simulate invalid id) -> invalid list
    class ReaderRaises:
        def __init__(self, db):
            pass

        async def get_job(self, job_id=None):
            if job_id == 'bad':
                raise RuntimeError('boom')
            return {"job_id": job_id, "user_id":"u-1"}

    monkeypatch.setattr(jpc, "JobPostReader", ReaderRaises)

    request2 = SimpleNamespace(state=SimpleNamespace(user={"user_id":"u-1","role":"HR"}))
    res2 = await jpc.delete_job_posts_batch_controller(job_ids=['bad'], request=request2)
    assert isinstance(res2, dict)
    assert res2.get('status_code') == status.HTTP_400_BAD_REQUEST

    # Case 3: UpdateService.delete_jobs_batch raises -> fallback to hard_delete_jobs_batch; test hard_delete_jobs_batch returns 0 -> 400; then cause hard_delete_jobs_batch to raise to reach exception path
    class FakeUpdateService:
        def __init__(self, db):
            pass

        async def delete_jobs_batch(self, job_ids):
            raise RuntimeError('boom-service')

    monkeypatch.setattr(jpc, "UpdateJobPost", FakeUpdateService)

    # If hard_delete_jobs_batch returns 0 -> returns 400
    async def fake_hard_delete_zero(db, job_ids):
        return 0

    monkeypatch.setattr(jpc, "hard_delete_jobs_batch", fake_hard_delete_zero)
    res3 = await jpc.delete_job_posts_batch_controller(job_ids=['111'], request=request2)
    assert isinstance(res3, dict)
    assert res3.get('status_code') == 400

    # If hard_delete_jobs_batch raises -> exception path
    async def fake_hard_delete_raise(db, job_ids):
        raise RuntimeError('boom-hard')

    monkeypatch.setattr(jpc, "hard_delete_jobs_batch", fake_hard_delete_raise)
    res4 = await jpc.delete_job_posts_batch_controller(job_ids=['111'], request=request2)
    assert isinstance(res4, dict)
    # Should return server error 500
    assert res4.get('status_code') == 500


# Done: tests for missing branches completed
