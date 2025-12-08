import pytest
import json

import app.controllers.email_template_controller as et_ctrl


@pytest.mark.asyncio
async def test_preview_rendering_exception_returns_500(monkeypatch):
    class BadService:
        @staticmethod
        async def get_template_preview_content(template_subject=None, template_body=None, sample_context=None):
            raise Exception("render-fail")

    monkeypatch.setattr(et_ctrl, "EmailTemplateService", BadService)

    # Create a minimal fake request object matching the expected schema fields
    fake_req = type("R", (), {"template_subject": "s", "template_body": "b", "sample_context": {}})()
    resp = await et_ctrl.handle_preview_email_template_controller(fake_req)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "render-fail" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_update_template_exception_returns_500(monkeypatch):
    class BadService2:
        @staticmethod
        async def save_email_template(db, template_key, subject, body):
            raise Exception("save-fail")

    monkeypatch.setattr(et_ctrl, "EmailTemplateService", BadService2)

    fake_req = type("R", (), {"template_key": "k", "subject_template": "s", "body_template_html": "b"})()
    resp = await et_ctrl.handle_update_email_template_controller(fake_req, db=None)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body.get("success") is False
    assert "save-fail" in (body.get("message") or "")
