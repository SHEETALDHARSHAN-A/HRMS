import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import json

from fastapi.responses import JSONResponse

import app.controllers.job_post_controller as jp_ctrl


async def _fake_get_db():
    yield AsyncMock()


@pytest.mark.asyncio
async def test_get_all_jobs_controller_reader_raises(monkeypatch):
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class BrokenReader:
        def __init__(self, db):
            pass

        def list_all(self):
            raise RuntimeError("reader fail")

    monkeypatch.setattr(jp_ctrl, "JobPostReader", BrokenReader)

    resp = await jp_ctrl.get_all_jobs_controller(request=None)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_active_jobs_controller_reader_raises(monkeypatch):
    monkeypatch.setattr(jp_ctrl, "get_db", _fake_get_db)

    class BrokenReader:
        def __init__(self, db):
            pass

        def list_active(self):
            raise RuntimeError("fail active")

    monkeypatch.setattr(jp_ctrl, "JobPostReader", BrokenReader)

    resp = await jp_ctrl.get_active_jobs_controller()
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_job_by_id_reader_and_getjobpost_raise(monkeypatch):
    # Use a valid UUID so controller proceeds to DB access
    valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
    async def fake_get_db():
        yield AsyncMock()
    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    class BadGet:
        def __init__(self, db):
            pass

        def fetch_full_job_details(self, job_id):
            raise RuntimeError("getjobpost fail")

    class BrokenReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            raise RuntimeError("reader fail too")

    monkeypatch.setattr(jp_ctrl, "GetJobPost", BadGet)
    monkeypatch.setattr(jp_ctrl, "JobPostReader", BrokenReader)

    resp = await jp_ctrl.get_job_by_id_controller(valid_uuid, request=None)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_toggle_job_status_reader_raises(monkeypatch):
    async def fake_get_db():
        yield AsyncMock()
    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    class BrokenReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            raise RuntimeError("no job for toggle")

    monkeypatch.setattr(jp_ctrl, "JobPostReader", BrokenReader)

    # request with a user
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1", "sub": "u1"}))
    resp = await jp_ctrl.toggle_job_status_controller("jid", True, request=request)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_delete_job_post_reader_raises(monkeypatch):
    async def fake_get_db():
        yield AsyncMock()
    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    class BrokenReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id=None):
            raise RuntimeError("reader explosion")

    monkeypatch.setattr(jp_ctrl, "JobPostReader", BrokenReader)
    request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1", "sub": "u1"}))
    resp = await jp_ctrl.delete_job_post_controller("jid", request=request)
    # controller may return either a JSONResponse or a dict (ResponseBuilder.server_error)
    if isinstance(resp, JSONResponse):
        assert resp.status_code == 500
    else:
        assert isinstance(resp, dict)
        assert resp.get("status_code") == 500


@pytest.mark.asyncio
async def test_search_public_jobs_service_raises(monkeypatch):
    class BadService:
        async def search_jobs(self, search_role=None, search_skills=None, search_locations=None):
            raise RuntimeError("search fail")

    res = await jp_ctrl.search_public_jobs_controller(search_service=BadService(), role="dev", skills=None, locations=None)
    # ResponseBuilder.server_error returns a dict, not JSONResponse, in this controller path
    assert isinstance(res, dict)
    assert res.get("status_code") == 500


@pytest.mark.asyncio
async def test_get_search_suggestions_service_raises(monkeypatch):
    class BadService:
        async def get_suggestions(self):
            raise RuntimeError("suggest fail")

    res = await jp_ctrl.get_search_suggestions_controller(search_service=BadService())
    assert isinstance(res, dict)
    assert res.get("status_code") == 500


@pytest.mark.asyncio
async def test_candidate_stats_repo_raises(monkeypatch):
    async def fake_get_db():
        yield AsyncMock()
    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    class BadRepo:
        def __init__(self, db):
            pass

        async def count_by_status(self, job_id, status="applied"):
            raise RuntimeError("repo fail")

    monkeypatch.setattr("app.db.repository.profile_repository.ProfileRepository", BadRepo)

    res = await jp_ctrl.candidate_stats_controller(job_id="123e4567-e89b-12d3-a456-426614174000")
    assert isinstance(res, dict) or hasattr(res, 'get')
    # server_error returns a dict with status_code 500
    assert res.get("status_code") == 500
