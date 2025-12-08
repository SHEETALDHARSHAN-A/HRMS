import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import ExpiredSignatureError, JWTError
import app.authentication.jwt_middleware as jwt_mw


def _make_app(excluded=None, role_protected=None):
    app = FastAPI()
    # set required state
    app.state.jwt_secret_key = "secret"
    app.state.jwt_algorithm = "HS256"

    kwargs = {}
    if excluded is not None:
        kwargs['excluded_routes'] = excluded
    if role_protected is not None:
        kwargs['role_protected_endpoints'] = role_protected

    app.add_middleware(jwt_mw.JWTMiddleware, **kwargs)

    @app.get("/open")
    def open():
        return {"ok": True}

    @app.get("/protected/{id}")
    def prot(id: str):
        return {"ok": True}

    return app


def test_no_token_returns_403():
    app = _make_app()
    client = TestClient(app)
    r = client.get("/open")
    assert r.status_code == 403
    assert r.json().get("detail") == "Authentication token missing."


def test_valid_token_calls_next(monkeypatch):
    app = _make_app()
    client = TestClient(app)

    # jwt.decode returns payload with jti and role
    monkeypatch.setattr(jwt_mw.jwt, "decode", lambda token, key, algorithms: {"jti": "j1", "role": "USER"})
    # Redis client and jti check
    class FakeRedis:
        async def get(self, k):
            return None

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    async def fake_revoked(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", fake_revoked)

    r = client.get("/open", headers={"Authorization": "Bearer tok"})
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_expired_signature_returns_401(monkeypatch):
    app = _make_app()
    client = TestClient(app)
    def raise_exp(*a, **k):
        raise ExpiredSignatureError("expired")
    monkeypatch.setattr(jwt_mw.jwt, "decode", raise_exp)
    class FakeRedis:
        async def get(self, k):
            return None
    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    r = client.get("/open", headers={"Authorization": "Bearer t"})
    assert r.status_code == 401
    assert r.json().get("detail") == "Token expired."


def test_jwt_error_returns_401(monkeypatch):
    app = _make_app()
    client = TestClient(app)
    def raise_jwt(*a, **k):
        raise JWTError("bad")
    monkeypatch.setattr(jwt_mw.jwt, "decode", raise_jwt)
    class FakeRedis:
        async def get(self, k):
            return None
    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    r = client.get("/open", headers={"Authorization": "Bearer t"})
    assert r.status_code == 401


def test_redis_get_client_raises_on_decode_returns_500(monkeypatch):
    app = _make_app()
    client = TestClient(app)
    # decode would succeed
    monkeypatch.setattr(jwt_mw.jwt, "decode", lambda token, key, algorithms: {"jti": "j1", "role": "USER"})
    # get_client raises ConnectionError
    def raise_conn():
        raise ConnectionError("no redis")
    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(raise_conn))

    r = client.get("/open", headers={"Authorization": "Bearer tok"})
    assert r.status_code == 500
    assert "Redis" in r.json().get("detail")


def test_temp_access_allows_call_next(monkeypatch):
    # When query param user_id present and redis.get returns truthy -> call_next
    app = _make_app()
    client = TestClient(app)

    class FakeRedis:
        async def get(self, k):
            return b"1"

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    r = client.get("/open?user_id=abc")
    # Because no token, but temp access returned True, middleware should allow
    assert r.status_code == 200


def test_jti_revoked_returns_401(monkeypatch):
    app = _make_app()
    client = TestClient(app)
    monkeypatch.setattr(jwt_mw.jwt, "decode", lambda token, key, algorithms: {"jti": "j1", "role": "USER"})
    class FakeRedis:
        async def get(self, k):
            return None

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    async def fake_revoked(j, r):
        return True
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", fake_revoked)

    r = client.get("/open", headers={"Authorization": "Bearer tok"})
    assert r.status_code == 401
    assert r.json().get("detail") == "Token revoked. Please log in again."


def test_missing_jti_returns_403(monkeypatch):
    app = _make_app()
    client = TestClient(app)
    monkeypatch.setattr(jwt_mw.jwt, "decode", lambda token, key, algorithms: {"sub": "u1"})
    class FakeRedis:
        async def get(self, k):
            return None

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    async def fake_revoked(j, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", fake_revoked)

    r = client.get("/open", headers={"Authorization": "Bearer tok"})
    assert r.status_code == 403
    assert "required ID (JTI)" in r.json().get("detail")


def test_role_protected_denied(monkeypatch):
    # Setup middleware with role-protected endpoint requiring ADMIN
    app = _make_app(role_protected={'/protected/{id}': ['ADMIN']})
    client = TestClient(app)

    monkeypatch.setattr(jwt_mw.jwt, "decode", lambda token, key, algorithms: {"jti": "j1", "role": "USER"})
    class FakeRedis:
        async def get(self, k):
            return None

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    async def fake_revoked(j, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", fake_revoked)

    r = client.get("/protected/123", headers={"Authorization": "Bearer tok"})
    assert r.status_code == 403
    assert r.json().get("detail") == "Access Denied."


def test_options_calls_next():
    # Ensure OPTIONS requests are allowed through
    app = _make_app()
    # Register an explicit OPTIONS handler so call_next returns 200.
    @app.options("/open")
    def open_options():
        return {"ok": True}

    client = TestClient(app)
    r = client.options("/open")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_refresh_token_cookie_used(monkeypatch):
    # When refresh_token cookie is present, middleware should pick it up
    app = _make_app()
    client = TestClient(app)

    # decode returns payload with jti and role
    monkeypatch.setattr(jwt_mw.jwt, "decode", lambda token, key, algorithms: {"jti": "jr", "role": "USER"})
    class FakeRedis:
        async def get(self, k):
            return None

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))
    async def fake_revoked(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", fake_revoked)

    # set refresh token cookie on client
    client.cookies.set("refresh_token", "rtok")
    r = client.get("/open")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_temp_access_redis_connection_error(monkeypatch):
    # Simulate Redis connection error during temp-access check -> should continue and return 403 (no token)
    app = _make_app()
    client = TestClient(app)

    def raise_conn():
        raise ConnectionError("redis down")

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(raise_conn))

    r = client.get("/open?user_id=abc")
    assert r.status_code == 403
    assert r.json().get("detail") == "Authentication token missing."


def test_generic_exception_returns_500(monkeypatch):
    # Force a non-JWT exception (ValueError) during decode -> should be caught by generic except and return 500
    app = _make_app()
    client = TestClient(app)

    def raise_val(*a, **k):
        raise ValueError("boom")

    monkeypatch.setattr(jwt_mw.jwt, "decode", raise_val)

    class FakeRedis:
        async def get(self, k):
            return None

    monkeypatch.setattr(jwt_mw.RedisManager, "get_client", staticmethod(lambda: FakeRedis()))

    r = client.get("/open", headers={"Authorization": "Bearer t"})
    assert r.status_code == 500
    assert "Server error" in r.json().get("detail")


def test_excluded_route_prefix_calls_next():
    # When an excluded route ends with '/' and the request path startswith it,
    # middleware should allow the request through without authentication.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    # set required state
    app.state.jwt_secret_key = "secret"
    app.state.jwt_algorithm = "HS256"

    # Excluded prefix ending with '/'
    app.add_middleware(jwt_mw.JWTMiddleware, excluded_routes=['/open/'])

    @app.get("/open/child")
    def child():
        return {"ok": True}

    client = TestClient(app)
    # No token provided, but path '/open/child' startswith '/open/' -> allowed
    r = client.get("/open/child")
    assert r.status_code == 200
    assert r.json().get("ok") is True
