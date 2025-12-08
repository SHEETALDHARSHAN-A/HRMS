from fastapi.testclient import TestClient
import main
import app.api.v1.invitation_routes as invitation_routes_mod
from app.db.connection_manager import get_db
from starlette.responses import JSONResponse
from jose import jwt as jose_jwt
import app.db.redis_manager as redis_manager
import app.utils.authentication_utils as auth_utils


def test_get_my_invitations_returns_dict(monkeypatch):
    client = TestClient(main.app)

    async def fake_get_my_invitations(request, db, status):
        return {"invitations": [], "status_code": 200}

    async def fake_get_db():
        yield None

    # patch the controller on the route module (call-site)
    monkeypatch.setattr(invitation_routes_mod, "handle_get_my_invitations_controller", fake_get_my_invitations)
    # override the DB dependency to avoid real DB calls
    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)

    # stub Redis and JTI revocation check so middleware accepts token
    class _DummyRedis:
        def get(self, *args, **kwargs):
            return None

    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _DummyRedis())
    monkeypatch.setattr(auth_utils, "is_jti_revoked", lambda jti, r: False)

    # build a token using app's secret and algorithm
    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "test-user", "jti": "test-jti-1", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    resp = client.get("/api/v1/invitations/my-invitations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"invitations": [], "status_code": 200}


def test_get_invitation_stats_returns_response_object(monkeypatch):
    client = TestClient(main.app)

    async def fake_get_stats(request, db):
        return JSONResponse(content={"stats": {"sent": 5}}, status_code=202)

    async def fake_get_db():
        yield None

    monkeypatch.setattr(invitation_routes_mod, "handle_get_invitation_stats_controller", fake_get_stats)
    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)

    # stub Redis and JTI revocation check so middleware accepts token
    class _DummyRedis2:
        def get(self, *args, **kwargs):
            return None

    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _DummyRedis2())
    monkeypatch.setattr(auth_utils, "is_jti_revoked", lambda jti, r: False)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "test-user", "jti": "test-jti-2", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    resp = client.get("/api/v1/invitations/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 202
    assert resp.json() == {"stats": {"sent": 5}}
