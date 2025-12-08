import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import status, HTTPException
from fastapi.responses import JSONResponse

import app.api.v1.job_post_routes as routes_mod
from app.api.v1.job_post_routes import job_post_routes_router
from app.utils.standard_response_utils import ResponseBuilder


def _make_app():
    app = FastAPI()
    app.include_router(job_post_routes_router)
    return app


def test_verify_internal_token_variants(monkeypatch):
    # Case: AppConfig has no token -> disabled
    class NoTokenConfig:
        def __init__(self):
            self.internal_service_token = None

    monkeypatch.setattr(routes_mod, "AppConfig", NoTokenConfig)
    with pytest.raises(HTTPException) as exc:
        routes_mod._verify_internal_token(None)
    assert exc.value.status_code == 403

    # Case: token set but header wrong -> Forbidden
    class HasTokenConfig:
        def __init__(self):
            self.internal_service_token = "secret"

    monkeypatch.setattr(routes_mod, "AppConfig", HasTokenConfig)
    with pytest.raises(HTTPException) as exc2:
        routes_mod._verify_internal_token("wrong")
    assert exc2.value.status_code == 403

    # Correct token returns True
    assert routes_mod._verify_internal_token("secret") is True


def test_analyze_upload_update_and_error_branches(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    # analyze endpoint -> controller returns success
    async def fake_analyze(job_details):
        return ResponseBuilder.success(message="analyzed", data={"ok": True})

    monkeypatch.setattr(routes_mod, "analyze_job_details_controller", fake_analyze)
    resp = client.post("/job-post/analyze", json={"job_title": "dev", "job_description": "x"})
    assert resp.status_code == 200
    assert resp.json().get("status_code") == status.HTTP_200_OK

    # upload endpoint -> override dependency and controller
    app.dependency_overrides[routes_mod.get_job_post_uploader] = lambda: "uploader"

    async def fake_upload(file, jd_uploader):
        return ResponseBuilder.success(message="uploaded", data={"uploaded": True})

    monkeypatch.setattr(routes_mod, "upload_job_post_controller", fake_upload)
    files = {"file": ("test.txt", b"hello world")}
    resp2 = client.post("/job-post/upload", files=files)
    assert resp2.status_code == 200
    assert resp2.json().get("status_code") == status.HTTP_200_OK

    # update endpoint -> controller returns dict with status_code -> JSONResponse path
    async def fake_update_dict(job_details, job_id, request):
        return {"status_code": status.HTTP_201_CREATED, "message": "created"}

    monkeypatch.setattr(routes_mod, "update_job_post_controller", fake_update_dict)
    headers = {"X-Test-User": "tester"}
    # Build minimal valid UpdateJdRequest payload
    payload = {
        "job_id": None,
        "job_title": "t",
        "job_description": "d",
        "description_sections": [],
        "minimum_experience": 0,
        "maximum_experience": 0,
        "no_of_openings": 1,
        "active_till": "2025-12-31T00:00:00Z",
        "skills_required": [{"skill": "Python", "weightage": 5}],
        "job_location": "",
        "role_fit": 0,
        "potential_fit": 0,
        "location_fit": 0,
    }
    resp3 = client.post("/job-post/update", json=payload, headers=headers)
    assert resp3.status_code == 201
    assert resp3.json().get("status_code") == status.HTTP_201_CREATED

    # update endpoint -> controller raises -> route catches and returns server_error dict
    async def fake_update_raise(job_details, job_id, request):
        raise Exception("boom")

    monkeypatch.setattr(routes_mod, "update_job_post_controller", fake_update_raise)
    resp4 = client.post("/job-post/update", json=payload)
    assert resp4.status_code == 200
    body4 = resp4.json()
    assert body4.get("status_code") == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "An unexpected error occurred" in body4.get("message", "")


def test_update_route_returns_response_object(monkeypatch):
    """When controller returns a Response object (not a dict), route should
    return it directly. This covers the `return result` path in the route.
    """
    app = _make_app()
    client = TestClient(app)

    async def fake_update_response(job_details, job_id, request):
        return JSONResponse(content={"ok": True}, status_code=202)

    monkeypatch.setattr(routes_mod, "update_job_post_controller", fake_update_response)

    headers = {"X-Test-User": "tester"}
    payload = {
        "job_id": None,
        "job_title": "t",
        "job_description": "d",
        "description_sections": [],
        "minimum_experience": 0,
        "maximum_experience": 0,
        "no_of_openings": 1,
        "active_till": "2025-12-31T00:00:00Z",
        "skills_required": [{"skill": "Python", "weightage": 5}],
        "job_location": "",
        "role_fit": 0,
        "potential_fit": 0,
        "location_fit": 0,
    }

    resp = client.post("/job-post/update", json=payload, headers=headers)
    assert resp.status_code == 202
    assert resp.json() == {"ok": True}


def test_my_jobs_agent_delete_batch_candidate_and_public(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    async def fake_my_jobs(request):
        return ResponseBuilder.success(message="my jobs", data={"count": 1})

    async def fake_my_agent_jobs(request):
        return ResponseBuilder.success(message="agent jobs", data={"count": 2})

    monkeypatch.setattr(routes_mod, "get_my_jobs_controller", fake_my_jobs)
    monkeypatch.setattr(routes_mod, "get_my_agent_jobs_controller", fake_my_agent_jobs)

    resp = client.get("/job-post/my-jobs")
    assert resp.status_code == 200
    assert resp.json().get("data", {}).get("count") == 1

    resp2 = client.get("/job-post/my-agent-jobs")
    assert resp2.status_code == 200
    assert resp2.json().get("data", {}).get("count") == 2

    # delete batch: dict input
    async def fake_delete_batch(job_ids, request):
        return ResponseBuilder.success(message="deleted", data={"ids": job_ids})

    monkeypatch.setattr(routes_mod, "delete_job_posts_batch_controller", fake_delete_batch)
    payload = {"job_ids": ["a", "b"]}
    resp3 = client.post("/job-post/delete-batch", json=payload)
    assert resp3.status_code == 200
    assert resp3.json().get("data", {}).get("ids") == ["a", "b"]

    # Note: route expects a dict body; posting a raw list yields 422 at validation time, so skip list-case

    # candidate stats
    async def fake_candidate_stats(job_id):
        return ResponseBuilder.success(message="stats", data={"job_id": job_id})

    monkeypatch.setattr(routes_mod, "candidate_stats_controller", fake_candidate_stats)
    resp5 = client.get("/job-post/candidate-stats/123")
    assert resp5.status_code == 200
    assert resp5.json().get("data", {}).get("job_id") == "123"

    # public job details
    async def fake_public_job(job_id):
        return ResponseBuilder.success(message="public", data={"job_id": job_id})

    monkeypatch.setattr(routes_mod, "get_public_job_by_id_controller", fake_public_job)
    resp6 = client.get("/job-post/public/job/321")
    assert resp6.status_code == 200
    assert resp6.json().get("data", {}).get("job_id") == "321"
