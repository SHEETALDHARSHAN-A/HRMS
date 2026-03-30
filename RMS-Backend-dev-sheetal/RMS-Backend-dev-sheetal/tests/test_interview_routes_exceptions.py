import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

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


def test_verify_internal_token_variants(monkeypatch):
    class NoTokenConfig:
        def __init__(self):
            self.internal_service_token = None

    monkeypatch.setattr(routes_mod, "AppConfig", NoTokenConfig)
    with pytest.raises(HTTPException) as exc:
        routes_mod._verify_internal_token(None)
    assert exc.value.status_code == 403

    class HasTokenConfig:
        def __init__(self):
            self.internal_service_token = "secret"

    monkeypatch.setattr(routes_mod, "AppConfig", HasTokenConfig)
    with pytest.raises(HTTPException) as exc2:
        routes_mod._verify_internal_token("wrong")
    assert exc2.value.status_code == 403

    assert routes_mod._verify_internal_token("secret") is True


def test_complete_interview_route_success_and_errors(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    class HasTokenConfig:
        def __init__(self):
            self.internal_service_token = "secret"

    monkeypatch.setattr(routes_mod, "AppConfig", HasTokenConfig)

    class SuccessService:
        def __init__(self, db):
            self.db = db

        async def complete_and_evaluate(self, token, email, session_id=None, final_notes=None):
            return {
                "token": token,
                "email": email,
                "decision": "shortlist",
                "currentRound": {"name": "Round 1"},
            }

    monkeypatch.setattr(routes_mod, "InterviewCompletionService", SuccessService)

    payload = {
        "email": "user@example.com",
        "token": "tok123456",
        "session_id": "11111111-1111-1111-1111-111111111111",
    }

    resp = client.post("/interview/complete", json=payload, headers={"x-internal-token": "secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status_code") == status.HTTP_200_OK
    assert body.get("data", {}).get("decision") == "shortlist"

    # Missing or wrong token is rejected by dependency before route executes.
    forbidden = client.post("/interview/complete", json=payload, headers={"x-internal-token": "wrong"})
    assert forbidden.status_code == 403

    class HttpErrorService:
        def __init__(self, db):
            self.db = db

        async def complete_and_evaluate(self, token, email, session_id=None, final_notes=None):
            raise HTTPException(status_code=404, detail="not found")

    monkeypatch.setattr(routes_mod, "InterviewCompletionService", HttpErrorService)
    not_found = client.post("/interview/complete", json=payload, headers={"x-internal-token": "secret"})
    assert not_found.status_code == 200
    body_nf = not_found.json()
    assert body_nf.get("status_code") == status.HTTP_404_NOT_FOUND

    class CrashService:
        def __init__(self, db):
            self.db = db

        async def complete_and_evaluate(self, token, email, session_id=None, final_notes=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(routes_mod, "InterviewCompletionService", CrashService)
    server_err = client.post("/interview/complete", json=payload, headers={"x-internal-token": "secret"})
    assert server_err.status_code == 200
    body_err = server_err.json()
    assert body_err.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR
