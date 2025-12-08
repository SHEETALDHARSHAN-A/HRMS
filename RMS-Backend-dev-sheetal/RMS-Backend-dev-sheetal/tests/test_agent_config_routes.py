import uuid
from types import SimpleNamespace
import pytest

from fastapi import HTTPException


def test__get_current_user_id_raises_when_no_sub():
    from app.api.v1.agent_config_routes import _get_current_user_id

    req = SimpleNamespace(state=SimpleNamespace(user={}))
    with pytest.raises(HTTPException) as ei:
        _get_current_user_id(req)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_update_agent_config_route_invalid_uuid_returns_error():
    from app.api.v1.agent_config_routes import update_agent_config_route
    from app.schemas.config_request import AgentConfigUpdateRequest

    req = SimpleNamespace(state=SimpleNamespace(user={"sub": "user-1"}))

    # Pass an invalid UUID for job_id
    bad_job_id = "not-a-uuid"
    payload = AgentConfigUpdateRequest(agentRounds=[])

    res = await update_agent_config_route(bad_job_id, req, payload, db=None)

    assert res["success"] is False
    assert res["status_code"] == 400
    assert "Invalid job ID format" in res["message"]


@pytest.mark.asyncio
async def test_update_agent_config_route_success(monkeypatch):
    from app.api.v1.agent_config_routes import update_agent_config_route
    from app.schemas.config_request import AgentConfigUpdateRequest, AgentRoundConfigUpdate

    job_id = str(uuid.uuid4())
    # Create a minimal round payload
    round_payload = AgentRoundConfigUpdate(
        jobId=job_id,
        roundListId=str(uuid.uuid4()),
        roundName="Round 1",
        roundFocus="Focus",
        persona="alex",
        keySkills=[],
        customQuestions=[],
        forbiddenTopics=[],
    )
    payload = AgentConfigUpdateRequest(agentRounds=[round_payload])

    req = SimpleNamespace(state=SimpleNamespace(user={"sub": str(uuid.uuid4())}))

    # Patch the AgentConfigService used by the route to return deterministic data
    class FakeService:
        def __init__(self, db):
            pass

        async def update_job_agent_config(self, job_id=None, user_id=None, rounds_data=None):
            return [
                {
                    "id": "1",
                    "jobId": job_id,
                    "roundListId": rounds_data[0].roundListId,
                    "roundName": rounds_data[0].roundName,
                    "roundFocus": rounds_data[0].roundFocus,
                    "persona": rounds_data[0].persona,
                    "keySkills": [],
                    "customQuestions": [],
                    "forbiddenTopics": [],
                    "scoreDistribution": None,
                }
            ]

    monkeypatch.setattr("app.api.v1.agent_config_routes.AgentConfigService", FakeService)

    res = await update_agent_config_route(job_id, req, payload, db=object())

    assert res["success"] is True
    assert "agentRounds" in res["data"]
    assert isinstance(res["data"]["agentRounds"], list)


@pytest.mark.asyncio
async def test_update_agent_config_route_propagates_http_exception(monkeypatch):
    """If service raises an HTTPException, the route should return that error status/message."""
    from fastapi import HTTPException
    from app.api.v1.agent_config_routes import update_agent_config_route
    from app.schemas.config_request import AgentConfigUpdateRequest

    job_id = str(uuid.uuid4())
    payload = AgentConfigUpdateRequest(agentRounds=[])
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": str(uuid.uuid4())}))

    class RaisingService:
        def __init__(self, db):
            pass

        async def update_job_agent_config(self, *a, **kw):
            raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr("app.api.v1.agent_config_routes.AgentConfigService", RaisingService)

    res = await update_agent_config_route(job_id, req, payload, db=object())
    assert res["success"] is False
    assert res["status_code"] == 403
    assert "forbidden" in res["message"].lower()


@pytest.mark.asyncio
async def test_update_agent_config_route_handles_generic_exception(monkeypatch):
    """If service raises a generic Exception, route should return server_error (500)."""
    from app.api.v1.agent_config_routes import update_agent_config_route
    from app.schemas.config_request import AgentConfigUpdateRequest

    job_id = str(uuid.uuid4())
    payload = AgentConfigUpdateRequest(agentRounds=[])
    req = SimpleNamespace(state=SimpleNamespace(user={"sub": str(uuid.uuid4())}))

    class RaisingService2:
        def __init__(self, db):
            pass

        async def update_job_agent_config(self, *a, **kw):
            raise Exception("boom")

    monkeypatch.setattr("app.api.v1.agent_config_routes.AgentConfigService", RaisingService2)

    res = await update_agent_config_route(job_id, req, payload, db=object())
    assert res["success"] is False
    assert res["status_code"] == 500
    assert "unexpected" in res["message"].lower() or "internal" in res["message"].lower()
import json
import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException, status

from app.services.config_service.agent_config_service import AgentConfigService


def make_agent_round(job_id=None):
    job_id = job_id or str(uuid.uuid4())
    return {
        "jobId": job_id,
        "roundListId": str(uuid.uuid4()),
        "roundName": "Round 1",
        "roundFocus": "focus",
        "persona": "alex",
        "keySkills": ["python"],
        "customQuestions": [],
        "forbiddenTopics": []
    }


@pytest.mark.asyncio
async def test_update_agent_config_success(client, monkeypatch):
    job_id = str(uuid.uuid4())
    payload = {"agentRounds": [make_agent_round(job_id=job_id)]}

    # Fake the AgentConfigService.update_job_agent_config method
    fake_return = [{"id": str(uuid.uuid4()), "jobId": job_id, "roundListId": payload["agentRounds"][0]["roundListId"],
                    "roundName": "Round 1", "roundFocus": "focus", "persona": "alex", "keySkills": ["python"],
                    "customQuestions": [], "forbiddenTopics": [], "scoreDistribution": {}}]

    async def fake_update_job_agent_config(self, job_id, user_id, rounds_data):
        assert job_id == job_id
        return fake_return

    monkeypatch.setattr(AgentConfigService, 'update_job_agent_config', fake_update_job_agent_config)

    # Provide a calling user in header
    header_val = json.dumps({"sub": "1111"})
    resp = client.post(f"/v1/agent-config/job/{job_id}", json=payload, headers={"x-test-user": header_val})
    assert resp.status_code == 200
    j = resp.json()
    assert j["success"] is True
    assert j["data"]["agentRounds"] == fake_return


@pytest.mark.asyncio
async def test_update_agent_config_unauthenticated(client, monkeypatch):
    job_id = str(uuid.uuid4())
    payload = {"agentRounds": [make_agent_round(job_id=job_id)]}

    resp = client.post(f"/v1/agent-config/job/{job_id}", json=payload)
    assert resp.status_code == 200
    j = resp.json()
    assert j["status_code"] == 401


@pytest.mark.asyncio
async def test_update_agent_config_invalid_job_id(client, monkeypatch):
    invalid_job_id = "not-a-uuid"
    payload = {"agentRounds": [make_agent_round(job_id=str(uuid.uuid4()))]}
    header_val = json.dumps({"sub": "1111"})
    resp = client.post(f"/v1/agent-config/job/{invalid_job_id}", json=payload, headers={"x-test-user": header_val})
    assert resp.status_code == 200
    j = resp.json()
    assert j["status_code"] == 400


@pytest.mark.asyncio
async def test_update_agent_config_service_http_exception(client, monkeypatch):
    job_id = str(uuid.uuid4())
    payload = {"agentRounds": [make_agent_round(job_id=job_id)]}
    header_val = json.dumps({"sub": "1111"})

    async def fake_update_raises(self, job_id, user_id, rounds_data):
        raise HTTPException(status_code=403, detail="Forbidden")

    monkeypatch.setattr(AgentConfigService, 'update_job_agent_config', fake_update_raises)

    resp = client.post(f"/v1/agent-config/job/{job_id}", json=payload, headers={"x-test-user": header_val})
    assert resp.status_code == 200
    j = resp.json()
    assert j["status_code"] == 403
