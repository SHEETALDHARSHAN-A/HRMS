import pytest
import asyncio
from types import SimpleNamespace

import app.controllers.job_post_controller as jp_ctrl


class DummyJobDetails:
    def __init__(self, job_id=None):
        self.job_id = job_id

    def model_dump(self):
        return {"job_id": self.job_id}


async def _fake_get_db():
    # mimic async generator dependency used by the controller
    yield "fake_db"


@pytest.mark.asyncio
async def test_get_all_jobs_controller_returns_jobs(monkeypatch):
    # Patch get_db to provide a fake DB
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class FakeReader:
        def __init__(self, db):
            self.db = db

        def list_all(self):
            return [{"id": "a", "title": "one"}, {"id": "b", "title": "two"}]

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)
    monkeypatch.setattr(jp_ctrl, "JobPostPermissions", SimpleNamespace(filter_jobs_by_ownership=lambda jobs, user, **kw: jobs))

    result = await jp_ctrl.get_all_jobs_controller(request=None)
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "jobs" in (result.get("data") or {})
    assert len(result["data"]["jobs"]) == 2


@pytest.mark.asyncio
async def test_get_my_jobs_controller_unauthenticated():
    # No state.user -> unauthorized
    req = SimpleNamespace()
    res = await jp_ctrl.get_my_jobs_controller(request=req)
    assert res.get("success") is False
    assert res.get("status_code") == 401


@pytest.mark.asyncio
async def test_get_my_jobs_controller_authenticated(monkeypatch):
    user = {"user_id": "user-1"}
    req = SimpleNamespace(state=SimpleNamespace(user=user))

    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def list_all(self):
            return []

        async def list_by_user(self, user_id):
            return [{"id": "x", "user_id": user_id}]

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)
    monkeypatch.setattr(jp_ctrl, "JobPostPermissions", SimpleNamespace(filter_jobs_by_ownership=lambda jobs, user, **kw: jobs))

    res = await jp_ctrl.get_my_jobs_controller(request=req)
    assert res.get("success") is True
    assert res.get("data") and isinstance(res.get("data").get("jobs"), list)


@pytest.mark.asyncio
async def test_update_job_post_controller_permission_denied(monkeypatch):
    # Setup request with user different than job owner
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-1"}))

    # Patch get_db and reader.get_job to return an existing job owned by someone else
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            return {"user_id": "other-user"}

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)

    # Ensure permissions check denies editing
    monkeypatch.setattr(jp_ctrl, "JobPostPermissions", SimpleNamespace(can_edit_job=lambda job, user: False))

    job_details = DummyJobDetails(job_id="job-1")

    resp = await jp_ctrl.update_job_post_controller(job_details=job_details, job_id="job-1", request=req)
    # Controller returns a JSONResponse on permission failure
    from fastapi.responses import JSONResponse
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_job_post_controller_success(monkeypatch):
    # Setup request with same user as owner
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-1", "user_id": "user-1"}))
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            return {"user_id": "user-1"}

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)

    # Allow editing
    monkeypatch.setattr(jp_ctrl, "JobPostPermissions", SimpleNamespace(can_edit_job=lambda job, user: True))

    # Fake UpdateJobPost service used inside controller
    class FakeUpdateService:
        def __init__(self, db):
            pass

        def update_job_post(self, job_details, job_id=None, creator_id=None):
            return {"success": True, "data": {"job_details": {"id": job_id or "new"}}, "status_code": 200}

    monkeypatch.setattr(jp_ctrl, "UpdateJobPost", FakeUpdateService)

    job_details = DummyJobDetails(job_id="job-1")
    res = await jp_ctrl.update_job_post_controller(job_details=job_details, job_id="job-1", request=req)
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert res.get("data") and res.get("data").get("job_details")


@pytest.mark.asyncio
async def test_analyze_job_details_controller(monkeypatch):
    # Patch analyzer service to return a predictable analysis
    class FakeAnalyzer:
        async def analyze_job_details(self, job_details=None):
            return {"score": 0.95}

    monkeypatch.setattr(jp_ctrl, "get_analyze_jd_service", lambda: FakeAnalyzer())

    dummy = SimpleNamespace()
    res = await jp_ctrl.analyze_job_details_controller(job_details=dummy)
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert res.get("data") and res.get("data").get("analysis_result").get("score") == 0.95


@pytest.mark.asyncio
async def test_update_job_post_controller_job_not_found(monkeypatch):
    # If reader.get_job returns None, controller should return 404
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-1"}))
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            return None

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)
    job_details = DummyJobDetails(job_id="job-missing")

    resp = await jp_ctrl.update_job_post_controller(job_details=job_details, job_id="job-missing", request=req)
    # Should return a JSONResponse with 404 status
    from fastapi.responses import JSONResponse
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_job_post_controller_service_failure(monkeypatch):
    # If the UpdateJobPost service returns success False, controller returns error
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-1", "user_id": "user-1"}))
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            return {"user_id": "user-1"}

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)
    monkeypatch.setattr(jp_ctrl, "JobPostPermissions", SimpleNamespace(can_edit_job=lambda job, user: True))

    class BadUpdateService:
        def __init__(self, db):
            pass

        def update_job_post(self, job_details, job_id=None, creator_id=None):
            return {"success": False, "message": "bad", "status_code": 500}

    monkeypatch.setattr(jp_ctrl, "UpdateJobPost", BadUpdateService)

    job_details = DummyJobDetails(job_id="job-1")
    res = await jp_ctrl.update_job_post_controller(job_details=job_details, job_id="job-1", request=req)
    assert res.get("success") is False
    assert res.get("status_code") == 500


@pytest.mark.asyncio
async def test_upload_job_post_controller_success(monkeypatch):
    # Patch uploader to return job_details
    class FakeUploader:
        async def job_details_file_upload(self, file=None):
            return {"job_details": {"title": "X"}}

    monkeypatch.setattr(jp_ctrl, "get_job_post_uploader", lambda: FakeUploader())

    # Create a dummy UploadFile-like object (only passed through)
    dummy_file = SimpleNamespace()
    res = await jp_ctrl.upload_job_post_controller(file=dummy_file, jd_uploader=FakeUploader())
    assert res.get("success") is True
    assert res.get("data") and res.get("data").get("extracted_details")


@pytest.mark.asyncio
async def test_upload_job_post_controller_error(monkeypatch):
    class ErrorUploader:
        async def job_details_file_upload(self, file=None):
            return {"error": "extraction failed"}

    monkeypatch.setattr(jp_ctrl, "get_job_post_uploader", lambda: ErrorUploader())
    dummy_file = SimpleNamespace()
    res = await jp_ctrl.upload_job_post_controller(file=dummy_file, jd_uploader=ErrorUploader())
    assert res.get("success") is False
    assert res.get("status_code") == 400


@pytest.mark.asyncio
async def test_upload_job_post_controller_exception(monkeypatch):
    class ExplodingUploader:
        async def job_details_file_upload(self, file=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(jp_ctrl, "get_job_post_uploader", lambda: ExplodingUploader())
    dummy_file = SimpleNamespace()
    res = await jp_ctrl.upload_job_post_controller(file=dummy_file, jd_uploader=ExplodingUploader())
    from fastapi.responses import JSONResponse
    assert isinstance(res, JSONResponse)
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_upload_job_post_controller_unexpected_output(monkeypatch):
    class WeirdUploader:
        async def job_details_file_upload(self, file=None):
            return {}

    monkeypatch.setattr(jp_ctrl, "get_job_post_uploader", lambda: WeirdUploader())
    dummy_file = SimpleNamespace()
    res = await jp_ctrl.upload_job_post_controller(file=dummy_file, jd_uploader=WeirdUploader())
    assert res.get("success") is False
    assert res.get("status_code") == 500


@pytest.mark.asyncio
async def test_update_job_post_controller_create_new_job(monkeypatch):
    # When job_id is not provided, controller should treat as create
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-2", "user_id": "user-2"}))
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    # No reader.get_job needed because final_job_id will be None
    class FakeUpdateService:
        def __init__(self, db):
            pass

        def update_job_post(self, job_details, job_id=None, creator_id=None):
            return {"success": True, "data": {"job_details": {"id": "new"}}, "status_code": 201}

    monkeypatch.setattr(jp_ctrl, "UpdateJobPost", FakeUpdateService)
    job_details = DummyJobDetails(job_id=None)
    res = await jp_ctrl.update_job_post_controller(job_details=job_details, job_id=None, request=req)
    assert res.get("success") is True
    assert res.get("status_code") == 201


@pytest.mark.asyncio
async def test_update_job_post_controller_get_job_awaitable(monkeypatch):
    # Simulate reader.get_job returning an awaitable (coroutine)
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-1"}))
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    async def coro_job():
        return {"user_id": "user-1"}

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            return coro_job()

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)
    monkeypatch.setattr(jp_ctrl, "JobPostPermissions", SimpleNamespace(can_edit_job=lambda job, user: True))
    class FakeUpdateService:
        def __init__(self, db):
            pass
        def update_job_post(self, job_details, job_id=None, creator_id=None):
            return {"success": True, "data": {"job_details": {"id": job_id}}, "status_code": 200}

    monkeypatch.setattr(jp_ctrl, "UpdateJobPost", FakeUpdateService)
    job_details = DummyJobDetails(job_id="job-await")
    res = await jp_ctrl.update_job_post_controller(job_details=job_details, job_id="job-await", request=req)
    assert res.get("success") is True
    assert res.get("data") and res.get("data").get("job_details")
import pytest
from types import SimpleNamespace

import app.controllers.job_post_controller as jp_ctrl


@pytest.mark.asyncio
async def test_get_my_jobs_unauthenticated():
    req = SimpleNamespace(state=SimpleNamespace(user=None))
    resp = await jp_ctrl.get_my_jobs_controller(req)
    assert resp["status_code"] == 401


@pytest.mark.asyncio
async def test_get_my_jobs_authenticated(monkeypatch):
    # Fake get_db async generator
    async def fake_get_db():
        yield "FAKE_DB"

    class FakeReader:
        def __init__(self, db):
            self.db = db

        async def list_by_user(self, user_id):
            return [{"id": "job1", "created_by_user_id": user_id}]

        async def list_all(self):
            return []

    monkeypatch.setattr(jp_ctrl, 'get_db', fake_get_db)
    monkeypatch.setattr(jp_ctrl, 'JobPostReader', FakeReader)
    monkeypatch.setattr(jp_ctrl, 'JobPostPermissions', type('X', (), {'filter_jobs_by_ownership': staticmethod(lambda jobs, user, show_own_only=True: jobs)}))

    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-123", "user_id": "user-123"}))
    resp = await jp_ctrl.get_my_jobs_controller(req)
    assert resp["status_code"] == 200
    assert resp["data"]["jobs"][0]["id"] == "job1"


@pytest.mark.asyncio
async def test_analyze_job_details_controller(monkeypatch):
    async def fake_analyze(job_details):
        return {"score": 0.9}

    monkeypatch.setattr(jp_ctrl, 'get_analyze_jd_service', lambda: type('A', (), {'analyze_job_details': staticmethod(fake_analyze)}))

    class FakeJobDetails:
        pass

    resp = await jp_ctrl.analyze_job_details_controller(FakeJobDetails())
    assert resp["status_code"] == 200
    assert resp["data"]["analysis_result"]["score"] == 0.9
