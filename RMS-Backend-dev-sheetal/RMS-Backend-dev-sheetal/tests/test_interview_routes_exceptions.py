from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import status

import app.api.v1.interview_routes as routes_mod
from app.api.v1.interview_routes import router as interview_router
from app.utils.standard_response_utils import ResponseBuilder


def _make_app():
    app = FastAPI()
    app.include_router(interview_router)
    return app


def test_validate_token_send_otp_happy_and_error(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_validate(email, token, db):
        return ResponseBuilder.success(message="otp sent", data={"sent": True})

    monkeypatch.setattr(routes_mod.InterviewAuthService, "validate_token_and_send_otp", fake_validate)

    payload = {"email": "user@example.com", "token": "tok"}
    resp = client.post("/interview/validate-token", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_200_OK
    assert body.get("data") == {"sent": True}

    async def server_err(email, token, db):
        return ResponseBuilder.server_error(message="bad")

    monkeypatch.setattr(routes_mod.InterviewAuthService, "validate_token_and_send_otp", server_err)
    resp2 = client.post("/interview/validate-token", json=payload)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_verify_otp_and_get_room_happy_and_error(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_verify(email, token, otp, db):
        return ResponseBuilder.success(message="ok", data={"room_url": "https://livekit.example/room"})

    monkeypatch.setattr(routes_mod.InterviewAuthService, "verify_otp_and_get_room", fake_verify)

    payload = {"email": "user@example.com", "token": "tok", "otp": "1234"}
    resp = client.post("/interview/verify-otp", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_200_OK
    assert body.get("data").get("room_url") == "https://livekit.example/room"

    async def server_err(email, token, otp, db):
        return ResponseBuilder.server_error(message="verify fail")

    monkeypatch.setattr(routes_mod.InterviewAuthService, "verify_otp_and_get_room", server_err)
    resp2 = client.post("/interview/verify-otp", json=payload)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR
