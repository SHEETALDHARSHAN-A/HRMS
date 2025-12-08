from fastapi import FastAPI
from fastapi.testclient import TestClient
import uuid

from app.api.v1.agent_config_routes import agent_config_router
from app.services.config_service.agent_config_service import AgentConfigService


def _make_app():
    app = FastAPI()
    app.include_router(agent_config_router)
    return app


def test_update_agent_config_handles_unexpected_exception(monkeypatch):
    # Prepare app and client
    app = _make_app()
    client = TestClient(app)

    # Use valid UUIDs
    job_id = "22222222-2222-2222-2222-222222222222"
    round_list_id = "33333333-3333-3333-3333-333333333333"

    # Monkeypatch the AgentConfigService.update_job_agent_config to raise
    async def fake_update(self, job_id_arg, user_id, rounds_data):
        raise Exception("simulated service failure")

    monkeypatch.setattr(AgentConfigService, "update_job_agent_config", fake_update)

    # Monkeypatch auth helper to bypass authentication and return a valid user id
    import app.api.v1.agent_config_routes as routes_mod

    monkeypatch.setattr(routes_mod, "_get_current_user_id", lambda request: "11111111-1111-1111-1111-111111111111")

    payload = {
        "agentRounds": [
            {
                "id": None,
                "jobId": job_id,
                "roundListId": round_list_id,
                "roundName": "Round 1",
                "roundFocus": "Focus",
                "persona": "alex",
                "keySkills": [],
                "customQuestions": [],
                "forbiddenTopics": []
            }
        ]
    }

    resp = client.post(f"/agent-config/job/{job_id}", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    # The route returns a ResponseBuilder.server_error dict; it contains status_code 500
    assert body.get("status_code") == 500
    assert body.get("success") is False
    assert "An unexpected error occurred" in body.get("message", "")


def test_update_agent_config_success(monkeypatch):
    # Prepare app and client
    app = _make_app()
    client = TestClient(app)

    # Use valid UUIDs
    job_id = "22222222-2222-2222-2222-222222222222"
    round_list_id = "33333333-3333-3333-3333-333333333333"

    # Monkeypatch the AgentConfigService.update_job_agent_config to return updated list
    async def fake_update(self, job_id, user_id, rounds_data):
        # Return a processed rounds list
        return [{"id": str(uuid.uuid4()), "jobId": job_id, "roundListId": round_list_id}]

    monkeypatch.setattr(AgentConfigService, "update_job_agent_config", fake_update)

    # Monkeypatch auth helper to bypass authentication and return a valid user id
    import app.api.v1.agent_config_routes as routes_mod

    monkeypatch.setattr(routes_mod, "_get_current_user_id", lambda request: "11111111-1111-1111-1111-111111111111")

    payload = {
        "agentRounds": [
            {
                "id": None,
                "jobId": job_id,
                "roundListId": round_list_id,
                "roundName": "Round 1",
                "roundFocus": "Focus",
                "persona": "alex",
                "keySkills": [],
                "customQuestions": [],
                "forbiddenTopics": []
            }
        ]
    }

    resp = client.post(f"/agent-config/job/{job_id}", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    # The route should return a success ResponseBuilder dict
    assert body.get("success") is True
    assert body.get("status_code") == 200
    assert body.get("data") and isinstance(body.get("data").get("agentRounds"), list)
