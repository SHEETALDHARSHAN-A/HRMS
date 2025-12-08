from fastapi.testclient import TestClient
import main
import app.api.v1.resume_routes as resume_routes_mod
from app.db.connection_manager import get_db
from starlette.responses import JSONResponse
from jose import jwt as jose_jwt
import app.db.redis_manager as redis_manager
import app.utils.authentication_utils as auth_utils


def _stub_redis():
    class _DummyRedis:
        def get(self, *args, **kwargs):
            return None

    return _DummyRedis()


def test_upload_resumes_returns_dict(monkeypatch):
    client = TestClient(main.app)

    async def fake_upload_resumes_controller(job_id, files, db):
        return {"status_code": 201, "uploaded": len(files)}

    async def fake_get_db():
        yield None

    monkeypatch.setattr(resume_routes_mod, "upload_resumes_controller", fake_upload_resumes_controller)
    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)

    # stub Redis and JTI revocation check so middleware accepts token
    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _stub_redis())
    monkeypatch.setattr(auth_utils, "is_jti_revoked", lambda jti, r: False)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "test-user", "jti": "test-jti-3", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    files = [
        ("files", ("a.pdf", b"dummy-pdf-data", "application/pdf")),
        ("files", ("b.pdf", b"more-pdf", "application/pdf")),
    ]

    resp = client.post(f"/api/v1/upload-resumes/12345", files=files, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json().get("uploaded") == 2


def test_upload_resumes_exception_path(monkeypatch):
    client = TestClient(main.app)

    async def fake_upload_resumes_controller(job_id, files, db):
        raise Exception("boom")

    async def fake_get_db():
        yield None

    monkeypatch.setattr(resume_routes_mod, "upload_resumes_controller", fake_upload_resumes_controller)
    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)

    # stub Redis and JTI revocation check so middleware accepts token
    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _stub_redis())
    monkeypatch.setattr(auth_utils, "is_jti_revoked", lambda jti, r: False)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "test-user", "jti": "test-jti-4", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    files = [("files", ("a.pdf", b"dummy-pdf-data", "application/pdf"))]

    resp = client.post(f"/api/v1/upload-resumes/67890", files=files, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 500
    body = resp.json()
    assert body.get("success") is False
    assert body.get("message") == "Failed to upload or queue resumes."
    assert any("boom" in e for e in body.get("errors", []))
