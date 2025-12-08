import pytest
from types import SimpleNamespace
from app.controllers import resume_controller as rc
from app.utils.standard_response_utils import ResponseBuilder
from fastapi import status


@pytest.mark.asyncio
async def test_handle_resume_upload_success_and_exception(monkeypatch):
    # Success with form metadata appended
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files, form_metadata=None, db=None):
            return {"status": "success", "saved_count": 1}

    monkeypatch.setattr(rc, "ResumeService", FakeService)
    files = []
    res = await rc.handle_resume_upload(job_id="j1", files=files, form_metadata={"a": 1}, db=None)
    assert isinstance(res, dict)
    assert res.get('status') == 'success'
    assert res.get('form_metadata') == {"a": 1}

    # Exception path - service raises
    class FakeServiceRaise:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files, form_metadata=None, db=None):
            raise RuntimeError('boom')

    monkeypatch.setattr(rc, "ResumeService", FakeServiceRaise)
    files = [{"filename": "f.pdf"}]
    res2 = await rc.handle_resume_upload(job_id="j1", files=files, form_metadata=None, db=None)
    assert isinstance(res2, dict)
    assert res2.get('saved_count') == 0
    assert res2.get('message')


@pytest.mark.asyncio
async def test_upload_resumes_controller_routes(monkeypatch):
    # Successful upload -> 202
    class FakeService:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files):
            return {
                "status": "success",
                "saved_count": 2,
                "skipped_files": [],
                "task_id": "t1",
                "saved_files": ["f1", "f2"]
            }

    monkeypatch.setattr(rc, "ResumeService", FakeService)
    res = await rc.upload_resumes_controller(job_id="j1", files=[{}], db=None)
    assert isinstance(res, dict)
    assert res.get('status_code') == status.HTTP_202_ACCEPTED

    # Partial success with skipped files -> 202
    class FakeServicePartial:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files):
            return {
                "status": "success",
                "saved_count": 1,
                "skipped_files": ["bad.pdf"],
                "message": "some skipped"
            }

    monkeypatch.setattr(rc, "ResumeService", FakeServicePartial)
    res2 = await rc.upload_resumes_controller(job_id="j1", files=[{}], db=None)
    assert isinstance(res2, dict)
    assert res2.get('status_code') == status.HTTP_202_ACCEPTED

    # Validation failure: saved_count == 0, skipped_files -> 400
    class FakeServiceValidation:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files):
            return {
                "status": "validation_failure",
                "saved_count": 0,
                "skipped_files": ["bad.pdf"],
                "message": "validation fail"
            }

    monkeypatch.setattr(rc, "ResumeService", FakeServiceValidation)
    res3 = await rc.upload_resumes_controller(job_id="j1", files=[{"filename":"bad.pdf"}], db=None)
    assert isinstance(res3, dict)
    assert res3.get('status_code') == status.HTTP_400_BAD_REQUEST

    # Server side error: status is not 'success' and no skipped files
    class FakeServiceError:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files):
            return {
                "status": "error",
                "saved_count": 0,
                "skipped_files": [],
                "message": "internal"
            }

    monkeypatch.setattr(rc, "ResumeService", FakeServiceError)
    res4 = await rc.upload_resumes_controller(job_id="j1", files=[{}], db=None)
    assert isinstance(res4, dict)
    # Controller treats zero saved_count as validation failure (400)
    assert res4.get('status_code') == 400

    # Service raises -> 500
    class FakeServiceRaise:
        def __init__(self, db):
            self.db = db

        async def process_resume_upload(self, job_id, files):
            raise RuntimeError('boom')

    monkeypatch.setattr(rc, "ResumeService", FakeServiceRaise)
    res5 = await rc.upload_resumes_controller(job_id="j1", files=[{}], db=None)
    assert isinstance(res5, dict)
    assert res5.get('status_code') == 500
