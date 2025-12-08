import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.api.v1.config_routes import router as config_router
from app.db.connection_manager import get_db
from app.services.config_service.email_template_service import EmailTemplateService


# --- Setup test app ---
app = FastAPI()
app.include_router(config_router, prefix="/v1")


async def fake_get_db():
    mock_db = AsyncMock()
    try:
        yield mock_db
    finally:
        pass


app.dependency_overrides[get_db] = fake_get_db

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_email_template_uses_defaults_when_missing(monkeypatch):
    # Fake service returns placeholders indicating missing content
    async def fake_get_template(db, key):
        return {"subject_template": "No Default", "body_template_html": "No Default"}

    monkeypatch.setattr("app.services.config_service.email_template_service.EmailTemplateService.get_template", fake_get_template)

    resp = client.get("/v1/config/email/template/OTP")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["success"] is True
    assert "data" in body


@pytest.mark.asyncio
async def test_preview_email_template_renders(monkeypatch):
    async def fake_preview(template_subject, template_body, sample_context):
        return ("SUBJ", "<p>BODY</p>")

    monkeypatch.setattr("app.services.config_service.email_template_service.EmailTemplateService.get_template_preview_content", fake_preview)

    payload = {"template_subject": "Hi {{name}}", "template_body": "Hello {{name}}", "sample_context": {"name": "Alice"}}
    resp = client.post("/v1/config/email/preview", json=payload)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["rendered_subject"] == "SUBJ"


@pytest.mark.asyncio
async def test_update_email_template_success(monkeypatch):
    async def fake_save(db, template_key, subject_template, body_template_html):
        return True

    monkeypatch.setattr("app.services.config_service.email_template_service.EmailTemplateService.save_email_template", fake_save)

    payload = {"template_key": "OTP", "subject_template": "S", "body_template_html": "B"}
    resp = client.post("/v1/config/email/template", json=payload)
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)


@pytest.mark.asyncio
async def test_reset_email_template_not_found_and_success(monkeypatch):
    async def fake_reset(db, template_key):
        # Simulate not found for first key, found for second
        return template_key == "FOUND"

    monkeypatch.setattr(EmailTemplateService, "reset_template_to_default", fake_reset)

    resp_not = client.post("/v1/config/email/template/NOTFOUND/reset")
    # Controller returns an error payload (HTTP 200) with status_code field set
    assert resp_not.status_code == status.HTTP_200_OK
    assert resp_not.json().get("status_code") == status.HTTP_404_NOT_FOUND

    resp_ok = client.post("/v1/config/email/template/FOUND/reset")
    assert resp_ok.status_code == status.HTTP_200_OK
    assert resp_ok.json().get("success") is True
import pytest

from app.api.v1 import config_routes as routes
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplateUpdateRequest


@pytest.mark.asyncio
async def test_preview_email_template_success(monkeypatch):
    async def fake_preview(template_subject, template_body, sample_context):
        return "Rendered Subject", "<p>Rendered Body</p>"

    monkeypatch.setattr(routes, "EmailTemplateService", type("X", (), {"get_template_preview_content": staticmethod(fake_preview)}))

    req = EmailTemplatePreviewRequest(
        template_subject="Hello {{NAME}}",
        template_body="<p>{{NAME}}</p>",
        sample_context={"NAME": "Alice"}
    )

    resp = await routes.preview_email_template(req)
    assert isinstance(resp, dict)
    assert resp["status_code"] == 200
    assert resp["data"]["rendered_subject"] == "Rendered Subject"


@pytest.mark.asyncio
async def test_update_email_template_created(monkeypatch):
    async def fake_save(db, template_key, subject_template, body_template_html):
        return True

    monkeypatch.setattr(routes, "EmailTemplateService", type("X", (), {"save_email_template": staticmethod(fake_save)}))

    req = EmailTemplateUpdateRequest(
        template_key="TEST_KEY",
        subject_template="Sub",
        body_template_html="<p>Body</p>"
    )

    # pass a fake db object
    resp = await routes.update_email_template(req, db="FAKE_DB")
    assert isinstance(resp, dict)
    assert resp["status_code"] == 201
    assert "updated successfully" in resp["message"]
