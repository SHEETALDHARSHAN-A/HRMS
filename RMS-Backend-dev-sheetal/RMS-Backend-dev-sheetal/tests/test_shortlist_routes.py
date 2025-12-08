from fastapi.testclient import TestClient
import main
import app.api.v1.shortlist_routes as sl_mod
from app.db.connection_manager import get_db
from jose import jwt as jose_jwt
import app.db.redis_manager as redis_manager
import app.utils.authentication_utils as auth_utils
from starlette.responses import JSONResponse


def _stub_redis():
    class _DummyRedis:
        def get(self, *args, **kwargs):
            return None
        async def exists(self, *args, **kwargs):
            return False
    return _DummyRedis()


def test_get_overview_and_get_candidates_and_update_status(monkeypatch):
    client = TestClient(main.app)

    async def fake_overview(db):
        return {"success": True, "status_code": 200, "message": "ok", "data": {"overview": []}}

    async def fake_get_candidates(job_id, round_id, result_filter, db):
        return {"success": True, "status_code": 200, "message": "ok", "data": {"candidates": []}}

    async def fake_update_status(profile_id, round_id, input, db):
        return JSONResponse(content={"success": True, "status_code": 200, "message": "updated", "data": {"updated": profile_id}}, status_code=200)

    async def fake_get_db():
        yield None

    monkeypatch.setattr(sl_mod, "get_job_round_overview_controller", fake_overview)
    monkeypatch.setattr(sl_mod, "get_all_candidates_controller", fake_get_candidates)
    monkeypatch.setattr(sl_mod, "update_candidate_status_controller", fake_update_status)

    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)
    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _stub_redis())
    import app.authentication.jwt_middleware as jwt_mw
    async def _async_false(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", _async_false)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "u-short", "jti": "short-jti-1", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    r = client.get("/api/v1/shortlist/overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json().get("data", {}).get("overview") == []

    r2 = client.get("/api/v1/shortlist/job-1/rounds/r1/candidates", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json().get("data", {}).get("candidates") == []

    body = {"new_result": "shortlisted", "reason": "Good"}
    r3 = client.patch("/api/v1/shortlist/rounds/r1/candidates/p-123/status", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json().get("data", {}).get("updated") == "p-123"
