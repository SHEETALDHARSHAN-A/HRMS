import pytest
from types import SimpleNamespace

# Ensure the expected dependency exists on the connection_manager before importing controller
import app.db.connection_manager as _conn
from unittest.mock import AsyncMock
if not hasattr(_conn, 'get_session'):
    async def _fake_get_session():
        mock_db = AsyncMock()
        try:
            yield mock_db
        finally:
            pass
    _conn.get_session = _fake_get_session

from app.controllers import config_controller as ctrl
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplateUpdateRequest


@pytest.mark.asyncio
async def test_preview_email_template_controller_success(monkeypatch):
    async def fake_preview(template_subject, template_body, sample_context):
        return ("Rendered Subject", "<p>Rendered Body</p>")

    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template_preview_content", fake_preview)

    req = EmailTemplatePreviewRequest(
        template_subject="Hi {{NAME}}",
        template_body="<p>{{NAME}}</p>",
        sample_context={"NAME": "Alice"}
    )

    resp = await ctrl.preview_email_template(req)
    assert isinstance(resp, dict)
    assert resp["status_code"] == 200
    assert resp["data"]["rendered_subject"] == "Rendered Subject"


@pytest.mark.asyncio
async def test_update_email_template_controller_success(monkeypatch):
    async def fake_save(db, template_key, subject_template, body_template_html):
        return True

    monkeypatch.setattr(ctrl.EmailTemplateService, "save_email_template", fake_save)

    req = EmailTemplateUpdateRequest(
        template_key="TEST",
        subject_template="Sub",
        body_template_html="<p>Body</p>"
    )

    # pass a fake db object (controller doesn't introspect it)
    resp = await ctrl.update_email_template(req, db=SimpleNamespace())
    assert isinstance(resp, dict)
    assert resp["status_code"] == 201
    assert "updated successfully" in resp["message"]


@pytest.mark.asyncio
async def test_preview_email_template_controller_value_error(monkeypatch):
    async def fake_preview(template_subject, template_body, sample_context):
        raise ValueError("Invalid template")

    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template_preview_content", fake_preview)

    req = EmailTemplatePreviewRequest(
        template_subject="Hi {{NAME}}",
        template_body="<p>{{NAME}}</p>",
        sample_context={"NAME": "Alice"}
    )

    resp = await ctrl.preview_email_template(req)
    assert isinstance(resp, dict)
    assert resp["status_code"] == 400
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_preview_email_template_controller_generic_exception(monkeypatch):
    async def fake_preview(template_subject, template_body, sample_context):
        raise Exception("Boom")

    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template_preview_content", fake_preview)

    req = EmailTemplatePreviewRequest(
        template_subject="Hi {{NAME}}",
        template_body="<p>{{NAME}}</p>",
        sample_context={"NAME": "Alice"}
    )

    resp = await ctrl.preview_email_template(req)
    assert isinstance(resp, dict)
    assert resp["status_code"] == 500
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_update_email_template_controller_save_false(monkeypatch):
    async def fake_save(db, template_key, subject_template, body_template_html):
        return False

    monkeypatch.setattr(ctrl.EmailTemplateService, "save_email_template", fake_save)
    req = EmailTemplateUpdateRequest(
        template_key="TEST",
        subject_template="Sub",
        body_template_html="<p>Body</p>"
    )
    resp = await ctrl.update_email_template(req, db=SimpleNamespace())
    assert isinstance(resp, dict)
    assert resp["status_code"] == 500
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_update_email_template_controller_runtime_error(monkeypatch):
    async def fake_save(db, template_key, subject_template, body_template_html):
        raise RuntimeError("DB fail")

    monkeypatch.setattr(ctrl.EmailTemplateService, "save_email_template", fake_save)
    req = EmailTemplateUpdateRequest(
        template_key="TEST",
        subject_template="Sub",
        body_template_html="<p>Body</p>"
    )
    resp = await ctrl.update_email_template(req, db=SimpleNamespace())
    assert isinstance(resp, dict)
    assert resp["status_code"] == 500
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_update_email_template_controller_generic_exception(monkeypatch):
    async def fake_save(db, template_key, subject_template, body_template_html):
        raise Exception("Unexpected")

    monkeypatch.setattr(ctrl.EmailTemplateService, "save_email_template", fake_save)
    req = EmailTemplateUpdateRequest(
        template_key="TEST",
        subject_template="Sub",
        body_template_html="<p>Body</p>"
    )
    resp = await ctrl.update_email_template(req, db=SimpleNamespace())
    assert isinstance(resp, dict)
    assert resp["status_code"] == 500
    assert resp["success"] is False
