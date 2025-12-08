import pytest
import json
from types import SimpleNamespace

import app.controllers.career_controller as career_ctrl


@pytest.mark.asyncio
async def test_verify_and_submit_returns_400_on_service_failure(monkeypatch):
    class FakeCareerService:
        def __init__(self, cache):
            pass

        async def verify_otp_and_submit_application(self, job_id, email, otp, application_data, db=None):
            return {"success": False, "message": "otp invalid"}

    monkeypatch.setattr(career_ctrl, "CareerApplicationService", FakeCareerService)

    resp = await career_ctrl.handle_verify_and_submit_controller(
        job_id="j1",
        email="e@x.com",
        otp="0000",
        files=None,
        application_data={},
        cache=None,
        db=None,
    )

    assert resp.status_code == 400
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "otp invalid" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_verify_and_submit_resume_processing_exception_sets_error(monkeypatch):
    # Service returns success with empty data
    class FakeCareerService2:
        def __init__(self, cache):
            pass

        async def verify_otp_and_submit_application(self, job_id, email, otp, application_data, db=None):
            return {"success": True, "data": {}, "status_code": 200}

    monkeypatch.setattr(career_ctrl, "CareerApplicationService", FakeCareerService2)

    # Monkeypatch the resume upload handler to raise an exception
    async def raise_upload(job_id, files, form_metadata, db=None):
        raise Exception("upload-fail")

    import app.controllers.resume_controller as resume_ctrl
    monkeypatch.setattr(resume_ctrl, "handle_resume_upload", raise_upload)

    files = [{"filename": "resume.pdf"}]
    application_data = {"first_name": "Bob", "last_name": "Smith", "phone": "123"}

    resp = await career_ctrl.handle_verify_and_submit_controller(
        job_id="j2",
        email="bob@example.com",
        otp="1111",
        files=files,
        application_data=application_data,
        cache=None,
        db=None,
    )

    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("success") is True
    data = body.get("data") or {}
    # resume_processing should contain the error string from the exception
    resume_proc = data.get("resume_processing")
    assert isinstance(resume_proc, dict)
    assert "upload-fail" in (resume_proc.get("error") or "")
import pytest
from types import SimpleNamespace

import app.controllers.career_controller as career


@pytest.mark.asyncio
async def test_send_career_otp_missing_fields():
    resp = await career.handle_send_career_otp_controller({}, cache=None)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_send_career_otp_success(monkeypatch):
    async def fake_send_otp(job_id, email, meta):
        return {"status_code": 200, "success": True, "message": "sent"}

    monkeypatch.setattr(career, 'CareerApplicationService', lambda cache: type('S', (), {'send_otp': staticmethod(fake_send_otp)})())

    payload = {"jobId": "j1", "email": "a@b.com", "firstName": "A"}
    resp = await career.handle_send_career_otp_controller(payload, cache=None)
    assert resp.status_code == 200
    import json
    body = json.loads(resp.body)
    assert body["success"] is True
