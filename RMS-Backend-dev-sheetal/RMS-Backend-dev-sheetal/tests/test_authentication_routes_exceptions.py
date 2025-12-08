from fastapi import FastAPI
from fastapi.testclient import TestClient
import urllib.parse
import fastapi.responses as responses

import app.api.v1.authentication_routes as routes_mod
from app.api.v1.authentication_routes import auth_router, admin_router


def _make_app():
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(admin_router)
    return app


def test_post_verify_email_update_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    # Monkeypatch the controller function used by the POST verify-email-update endpoint
    async def fake_verify(*args, **kwargs):
        raise Exception("verify-email failure")

    monkeypatch.setattr(routes_mod, "handle_verify_admin_email_update_controller", fake_verify)

    payload = {"user_id": "u1", "token": "t1", "new_email": "n@example.com"}

    resp = client.post("/admins/verify-email-update", json=payload)

    assert resp.status_code == 500
    body = resp.json()
    assert body.get("success") is False
    assert body.get("status_code") == 500
    assert "verify-email failure" in body.get("message", "")


def test_confirm_phone_update_exception_redirect(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_confirm(*args, **kwargs):
        raise Exception("phone confirm boom")

    monkeypatch.setattr(routes_mod, "handle_verify_admin_phone_update_controller", fake_confirm)

    # Ensure frontend_url is set to a known value
    monkeypatch.setattr(routes_mod.settings, "frontend_url", "http://frontend.test")

    # Replace RedirectResponse so the route does not try to actually redirect
    def fake_redirect(url, status_code=None):
        return routes_mod.ResponseBuilder.success("redirect", data={"url": url})

    monkeypatch.setattr(responses, "RedirectResponse", fake_redirect)

    resp = client.get("/admins/confirm-phone-update", params={"token": "t", "user_id": "u"})
    body = resp.json()
    assert body.get("success") is True
    assert "phone_update_error" in body.get("data", {}).get("url", "")


import pytest


@pytest.mark.asyncio
async def test_complete_email_update_status_exception_redirect_and_fallback(monkeypatch):
    async def fake_complete(*args, **kwargs):
        raise Exception("complete email boom")

    monkeypatch.setattr(routes_mod, "handle_complete_email_update_controller", fake_complete)

    # Case 1: with redirect_to -> expect RedirectResponse to that URL with encoded error
    redirect_to = "http://app.local/return"

    # Replace RedirectResponse so we can examine the produced URL
    def fake_redirect2(url, status_code=None):
        return routes_mod.ResponseBuilder.success("redirect", data={"url": url})

    monkeypatch.setattr(responses, "RedirectResponse", fake_redirect2)
    monkeypatch.setattr(routes_mod, "RedirectResponse", fake_redirect2)

    # Build a minimal Request for direct call (not used by the handler)
    from starlette.requests import Request
    scope = {"type": "http", "method": "GET", "path": "/"}
    request = Request(scope)

    result = await routes_mod.complete_email_update_status_endpoint(
        request,
        "t",
        "u",
        "n@example.com",
        redirect_to,
        db=None,
        cache=None,
        response=None,
    )

    # Support both the fake-dict returned by our monkeypatch and a real RedirectResponse
    if hasattr(result, "get"):
        # dict-like
        assert result.get("success") is True
        loc = result.get("data", {}).get("url", "")
    else:
        # Could be an actual RedirectResponse object
        loc = result.headers.get("location", "")
    assert loc.startswith(redirect_to)
    assert "error=" in loc
    assert urllib.parse.quote_plus("complete email boom") in loc

    # Case 2: without redirect_to -> expect ResponseBuilder.server_error dict returned
    result2 = await routes_mod.complete_email_update_status_endpoint(
        request,
        "t",
        "u",
        "n@example.com",
        None,
        db=None,
        cache=None,
        response=None,
    )

    assert result2.get("status_code") == 500
    assert result2.get("success") is False


def test_verify_name_update_exception(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_name(*args, **kwargs):
        raise Exception("name update fail")

    monkeypatch.setattr(routes_mod, "handle_verify_admin_name_update_controller", fake_name)

    resp = client.get("/admins/verify-name-update", params={"user_id": "u1", "token": "t1"})
    assert resp.status_code == 500
    body = resp.json()
    assert body.get("status_code") == 500
    assert body.get("success") is False
    assert "An unexpected error occurred" in body.get("message", "")
