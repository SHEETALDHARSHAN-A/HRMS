from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.career_routes import career_router
from app.api.v1.interview_routes import router as interview_router
from app.db.connection_manager import get_db
from app.db.redis_manager import get_redis_client

import app.controllers.career_controller as career_ctrl
import app.api.v1.interview_routes as interview_routes_mod


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(career_router)
    app.include_router(interview_router)

    async def _fake_get_db():
        yield object()

    async def _fake_get_cache():
        class _DummyCache:
            pass

        yield _DummyCache()

    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_redis_client] = _fake_get_cache
    return app


def test_career_submit_to_agent_interview_complete_flow(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_verify_and_submit(self, job_id, email, otp, application_data, db):
        return {
            "success": True,
            "message": "Application submitted successfully",
            "data": {"application_id": "app_1"},
            "status_code": 200,
        }

    async def fake_resume_upload(job_id, files, form_metadata, db=None):
        return {"task_id": "task_1", "saved_count": 1}

    monkeypatch.setattr(
        career_ctrl.CareerApplicationService,
        "verify_otp_and_submit_application",
        fake_verify_and_submit,
    )
    monkeypatch.setattr(
        "app.controllers.resume_controller.handle_resume_upload",
        fake_resume_upload,
    )

    apply_resp = client.post(
        "/career/apply/verify-and-submit",
        data={
            "jobId": "11111111-1111-1111-1111-111111111111",
            "email": "candidate@example.com",
            "otp": "123456",
            "firstName": "Career",
            "lastName": "Candidate",
            "phone": "1234567890",
        },
        files={"resume": ("resume.pdf", b"%PDF-test", "application/pdf")},
    )

    assert apply_resp.status_code == 200
    apply_body = apply_resp.json()
    assert apply_body.get("success") is True
    assert apply_body.get("data", {}).get("application_id") == "app_1"
    assert apply_body.get("data", {}).get("resume_processing", {}).get("task_id") == "task_1"

    class HasTokenConfig:
        def __init__(self):
            self.internal_service_token = "internal-secret"

    monkeypatch.setattr(interview_routes_mod, "AppConfig", HasTokenConfig)

    class FakeCompletionService:
        def __init__(self, db):
            self.db = db

        async def complete_and_evaluate(self, token, email, session_id=None, final_notes=None):
            return {
                "token": token,
                "email": email,
                "decision": "shortlist",
                "roundStatus": "shortlisted",
            }

    monkeypatch.setattr(interview_routes_mod, "InterviewCompletionService", FakeCompletionService)

    complete_resp = client.post(
        "/interview/complete",
        json={
            "token": "tok123456",
            "email": "candidate@example.com",
            "session_id": "11111111-1111-1111-1111-111111111111",
        },
        headers={"x-internal-token": "internal-secret"},
    )

    assert complete_resp.status_code == 200
    complete_body = complete_resp.json()
    assert complete_body.get("success") is True
    assert complete_body.get("data", {}).get("decision") == "shortlist"
