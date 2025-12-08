from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import status

import app.api.v1.email_template_routes as routes_mod
from app.api.v1.email_template_routes import router as email_router
from app.utils.standard_response_utils import ResponseBuilder


def _make_app():
    app = FastAPI()
    app.include_router(email_router)
    return app


def test_get_email_template_happy_path_and_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_handle_get(template_key, db):
        return ResponseBuilder.success(message="ok", data={"k": "v"})

    monkeypatch.setattr(routes_mod, "handle_get_email_template_controller", fake_handle_get)

    resp = client.get("/email-templates/SOME_KEY")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_200_OK
    assert body.get("data") == {"k": "v"}

    # controller returns server error dict -> route should return that JSON
    async def server_err(template_key, db):
        return ResponseBuilder.server_error(message="boom")

    monkeypatch.setattr(routes_mod, "handle_get_email_template_controller", server_err)
    resp2 = client.get("/email-templates/SOME_KEY")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_preview_email_template_happy_and_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_preview(request):
        return ResponseBuilder.success(message="previewed", data={"rendered_html_body": "<p>x</p>"})

    monkeypatch.setattr(routes_mod, "handle_preview_email_template_controller", fake_preview)

    payload = {"template_subject": "s", "template_body": "b", "sample_context": {}}
    resp = client.post("/email-templates/preview", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_200_OK
    assert body.get("data").get("rendered_html_body") == "<p>x</p>"

    async def server_err_preview(request):
        return ResponseBuilder.server_error(message="render fail")

    monkeypatch.setattr(routes_mod, "handle_preview_email_template_controller", server_err_preview)
    resp2 = client.post("/email-templates/preview", json=payload)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_update_email_template_happy_and_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_update(request, db):
        return ResponseBuilder.created(message="created")

    monkeypatch.setattr(routes_mod, "handle_update_email_template_controller", fake_update)

    payload = {"template_key": "TKEY", "subject_template": "s", "body_template_html": "b"}
    resp = client.post("/email-templates", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_201_CREATED

    async def server_err_update(request, db):
        return ResponseBuilder.server_error(message="save fail")

    monkeypatch.setattr(routes_mod, "handle_update_email_template_controller", server_err_update)
    resp2 = client.post("/email-templates", json=payload)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR
