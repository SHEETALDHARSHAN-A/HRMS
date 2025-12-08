from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import status

import app.api.v1.config_routes as routes_mod
from app.api.v1.config_routes import router as config_router


def _make_app():
    app = FastAPI()
    app.include_router(config_router)
    return app


def test_get_email_template_no_default_mapping(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    # return values that indicate "No Default..." so fallback runs
    async def fake_get_template(db, key):
        return {"subject_template": "No Default subject", "body_template_html": "No Default body"}

    monkeypatch.setattr(routes_mod.EmailTemplateService, "get_template", fake_get_template)

    resp = client.get("/config/email/template/UNMAPPED_KEY")
    assert resp.status_code == 200
    body = resp.json()
    # The controller fallback finds no mapping and logs debug; data remains present
    assert body["data"]["subject_template"].startswith("No Default")


def test_get_email_template_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    def raise_exc(db, key):
        raise Exception("backend fail")

    monkeypatch.setattr(routes_mod.EmailTemplateService, "get_template", raise_exc)

    resp = client.get("/config/email/template/SOME_KEY")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == 500
    assert body.get("message") == "Error retrieving template from backend."


def test_preview_email_template_valueerror_and_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    # ValueError -> should return error with status_code 400
    async def raise_valueerror(**kwargs):
        raise ValueError("bad template")

    monkeypatch.setattr(routes_mod.EmailTemplateService, "get_template_preview_content", raise_valueerror)

    payload = {"template_subject": "s", "template_body": "b", "sample_context": {}}
    resp = client.post("/config/email/preview", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_400_BAD_REQUEST

    # General exception -> should return server_error with status_code 500
    async def raise_exc(**kwargs):
        raise Exception("render fail")

    monkeypatch.setattr(routes_mod.EmailTemplateService, "get_template_preview_content", raise_exc)
    resp2 = client.post("/config/email/preview", json=payload)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == 500


def test_update_email_template_branches(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    payload = {"template_key": "TKEY", "subject_template": "s", "body_template_html": "b"}

    # Case: save returns False -> returns error with 500
    async def save_false(db, template_key, subject_template, body_template_html):
        return False

    monkeypatch.setattr(routes_mod.EmailTemplateService, "save_email_template", save_false)
    resp = client.post("/config/email/template", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Case: RuntimeError -> server_error with DB message
    async def raise_runtime(db, template_key, subject_template, body_template_html):
        raise RuntimeError("db down")

    monkeypatch.setattr(routes_mod.EmailTemplateService, "save_email_template", raise_runtime)
    resp2 = client.post("/config/email/template", json=payload)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == 500
    assert "Database error during template save" in body2.get("message", "")

    # Case: generic Exception -> server_error with unexpected message
    async def raise_exc(db, template_key, subject_template, body_template_html):
        raise Exception("boom")

    monkeypatch.setattr(routes_mod.EmailTemplateService, "save_email_template", raise_exc)
    resp3 = client.post("/config/email/template", json=payload)
    assert resp3.status_code == 200
    body3 = resp3.json()
    assert body3.get("status_code") == 500
    assert "An unexpected error occurred" in body3.get("message", "")


def test_reset_email_template_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def raise_exc(db, template_key):
        raise Exception("reset fail")

    monkeypatch.setattr(routes_mod.EmailTemplateService, "reset_template_to_default", raise_exc)

    resp = client.post("/config/email/template/SOME/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == 500
    assert "Error resetting template to default." in body.get("message", "")
