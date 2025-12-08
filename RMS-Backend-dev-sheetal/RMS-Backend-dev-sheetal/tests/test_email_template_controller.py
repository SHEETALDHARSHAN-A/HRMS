import pytest
import json
from unittest.mock import AsyncMock
from types import SimpleNamespace
from app.controllers import email_template_controller as ctrl
from app.schemas.config_request import EmailTemplatePreviewRequest, EmailTemplateUpdateRequest


@pytest.mark.asyncio
async def test_handle_get_email_template_controller_success(monkeypatch, fake_db):
    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template", AsyncMock(return_value={"template_key": "K"}))
    resp = await ctrl.handle_get_email_template_controller("K", fake_db)
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["success"] is True


@pytest.mark.asyncio
async def test_handle_get_email_template_controller_error(monkeypatch, fake_db):
    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template", AsyncMock(side_effect=Exception("fail")))
    resp = await ctrl.handle_get_email_template_controller("K", fake_db)
    assert resp.status_code == 500
    data = json.loads(resp.body)
    assert data["success"] is False


@pytest.mark.asyncio
async def test_handle_preview_email_template_controller_success(monkeypatch):
    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template_preview_content", AsyncMock(return_value=("S", "B")))
    req = EmailTemplatePreviewRequest(template_subject="Hi {{NAME}}", template_body="<p>{{NAME}}</p>", sample_context={"NAME": "A"})
    resp = await ctrl.handle_preview_email_template_controller(req)
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["success"] is True


@pytest.mark.asyncio
async def test_handle_preview_email_template_controller_value_error(monkeypatch):
    from fastapi import HTTPException
    async def bad_preview(*a, **k):
        raise ValueError("bad")
    monkeypatch.setattr(ctrl.EmailTemplateService, "get_template_preview_content", bad_preview)
    req = EmailTemplatePreviewRequest(template_subject="Hi", template_body="<p></p>", sample_context={})
    resp = await ctrl.handle_preview_email_template_controller(req)
    assert resp.status_code == 400
    assert json.loads(resp.body)["success"] is False


@pytest.mark.asyncio
async def test_handle_update_email_template_controller_success(monkeypatch, fake_db):
    monkeypatch.setattr(ctrl.EmailTemplateService, "save_email_template", AsyncMock(return_value=True))
    req = EmailTemplateUpdateRequest(template_key="T", subject_template="S", body_template_html="B")
    resp = await ctrl.handle_update_email_template_controller(req, fake_db)
    assert resp.status_code == 201
    assert json.loads(resp.body)["success"] is True


@pytest.mark.asyncio
async def test_handle_update_email_template_controller_failure(monkeypatch, fake_db):
    monkeypatch.setattr(ctrl.EmailTemplateService, "save_email_template", AsyncMock(return_value=False))
    req = EmailTemplateUpdateRequest(template_key="T", subject_template="S", body_template_html="B")
    resp = await ctrl.handle_update_email_template_controller(req, fake_db)
    assert resp.status_code == 500
    assert json.loads(resp.body)["success"] is False
