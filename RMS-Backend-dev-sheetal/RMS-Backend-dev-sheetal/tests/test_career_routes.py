import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

import app.controllers.career_controller as career_ctrl
from app.services.job_post.career_application_service import CareerApplicationService


@pytest.mark.asyncio
async def test_career_send_otp_missing_fields(client):
    # Missing email or jobId should return 400
    resp = client.post("/v1/career/apply/send-otp", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_career_send_otp_success(monkeypatch, client, fake_cache):
    payload = {"jobId": "j1", "email": "a@b.com"}
    async def fake_send_otp(self, job_id, email, meta):
        return {"success": True, "message": "OTP sent", "status_code": 200}

    monkeypatch.setattr(CareerApplicationService, 'send_otp', fake_send_otp)
    resp = client.post("/v1/career/apply/send-otp", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_career_verify_and_submit_missing_fields(client):
    resp = client.post("/v1/career/apply/verify-and-submit", data={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_career_verify_and_submit_success(monkeypatch, client, fake_db, fake_cache):
    # Prepare form data for request
    data = {
        "jobId": "j1",
        "email": "a@b.com",
        "otp": "1234",
        "firstName": "A",
        "lastName": "B",
    }

    # Fake service verify_otp_and_submit_application
    async def fake_verify_otp_and_submit(self, job_id, email, otp, application_data, db):
        return {"success": True, "message": "Submitted", "data": {"application_id": application_data.get("application_id")}, "status_code": 200}

    monkeypatch.setattr(CareerApplicationService, 'verify_otp_and_submit_application', fake_verify_otp_and_submit)

    resp = client.post("/v1/career/apply/verify-and-submit", data=data)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_career_verify_and_submit_with_file(monkeypatch, client, fake_db, fake_cache):
    data = {
        "jobId": "j1",
        "email": "a@b.com",
        "otp": "1234",
        "firstName": "A",
        "lastName": "B",
    }

    async def fake_verify_otp_and_submit(self, job_id, email, otp, application_data, db):
        return {"success": True, "message": "Submitted", "data": {}, "status_code": 200}

    async def fake_handle_resume_upload(job_id, files, form_metadata, db=None):
        return {"task_id": "t1"}

    monkeypatch.setattr(CareerApplicationService, 'verify_otp_and_submit_application', fake_verify_otp_and_submit)
    monkeypatch.setattr('app.controllers.resume_controller.handle_resume_upload', fake_handle_resume_upload)

    files = {"resume": ("resume.txt", b"content", "text/plain")}
    resp = client.post("/v1/career/apply/verify-and-submit", data=data, files=files)
    assert resp.status_code == 200
    assert resp.json()["data"].get("resume_processing")
