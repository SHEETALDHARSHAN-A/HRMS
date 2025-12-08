import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, Response
from starlette.datastructures import Headers
from app.authentication.jwt_middleware import JWTMiddleware
from jose import jwt, ExpiredSignatureError, JWTError

# Helper to build a mock request
def build_request(path="/v1/protected", headers=None, cookies=None, query_params=None):
    scope = {
        "type": "http",
        "path": path,
        "method": "GET",
        "headers": Headers(headers or {}).raw,
        "query_string": b""
    }
    request = Request(scope)
    request._cookies = cookies or {}
    if query_params:
        request.scope["query_string"] = "&".join([f"{k}={v}" for k, v in query_params.items()]).encode()
    
    # Mock app state (use scope since Request.app is read-only)
    app_mock = MagicMock()
    app_mock.state.jwt_secret_key = "secret"
    app_mock.state.jwt_algorithm = "HS256"
    request.scope["app"] = app_mock
    return request

@pytest.mark.asyncio
async def test_middleware_options_bypass():
    mw = JWTMiddleware(app=MagicMock())
    req = build_request(path="/v1/protected")
    req.scope["method"] = "OPTIONS"
    
    async def call_next(r): return "ok"
    res = await mw.dispatch(req, call_next)
    assert res == "ok"

@pytest.mark.asyncio
async def test_middleware_excluded_routes():
    mw = JWTMiddleware(app=MagicMock())
    # /docs is excluded by default
    req = build_request(path="/docs")
    async def call_next(r): return "ok"
    res = await mw.dispatch(req, call_next)
    assert res == "ok"

@pytest.mark.asyncio
async def test_middleware_temp_access_via_redis(monkeypatch):
    mw = JWTMiddleware(app=MagicMock())
    
    # Mock Redis to return True for temp access
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "1"
    monkeypatch.setattr("app.authentication.jwt_middleware.RedisManager.get_client", lambda: mock_redis)
    
    req = build_request(path="/v1/protected", query_params={"user_id": "u1"})
    
    async def call_next(r): return "ok"
    res = await mw.dispatch(req, call_next)
    assert res == "ok"
    mock_redis.get.assert_called_with("temp_access:u1")

@pytest.mark.asyncio
async def test_middleware_token_revocation_check(monkeypatch):
    mw = JWTMiddleware(app=MagicMock())
    
    token = jwt.encode({"sub": "u1", "jti": "j1", "role": "ADMIN"}, "secret", algorithm="HS256")
    req = build_request(headers={"Authorization": f"Bearer {token}"})
    
    mock_redis = AsyncMock()
    monkeypatch.setattr("app.authentication.jwt_middleware.RedisManager.get_client", lambda: mock_redis)
    # Mock is_jti_revoked to return True
    monkeypatch.setattr("app.authentication.jwt_middleware.is_jti_revoked", AsyncMock(return_value=True))
    
    res = await mw.dispatch(req, lambda r: "ok")
    assert res.status_code == 401
    import json
    body = json.loads(res.body)
    assert "revoked" in body["detail"]

@pytest.mark.asyncio
async def test_middleware_revocation_redis_fail_open(monkeypatch):
    """If Redis fails during revocation check, should allow access (fail open)."""
    mw = JWTMiddleware(app=MagicMock())
    token = jwt.encode({"sub": "u1", "jti": "j1", "role": "ADMIN"}, "secret", algorithm="HS256")
    req = build_request(headers={"Authorization": f"Bearer {token}"})
    
    mock_redis = AsyncMock()
    monkeypatch.setattr("app.authentication.jwt_middleware.RedisManager.get_client", lambda: mock_redis)
    
    # is_jti_revoked raises exception
    monkeypatch.setattr("app.authentication.jwt_middleware.is_jti_revoked", AsyncMock(side_effect=Exception("Redis down")))
    
    async def call_next(r): return "ok"
    res = await mw.dispatch(req, call_next)
    assert res == "ok" # Should proceed

@pytest.mark.asyncio
async def test_middleware_role_mismatch(monkeypatch):
    # Define a protected route requiring SUPER_ADMIN
    protected = {"/v1/super-only": ["SUPER_ADMIN"]}
    mw = JWTMiddleware(app=MagicMock(), role_protected_endpoints=protected)
    
    token = jwt.encode({"sub": "u1", "jti": "j1", "role": "HR"}, "secret", algorithm="HS256")
    req = build_request(path="/v1/super-only", headers={"Authorization": f"Bearer {token}"})
    
    mock_redis = AsyncMock()
    monkeypatch.setattr("app.authentication.jwt_middleware.RedisManager.get_client", lambda: mock_redis)
    monkeypatch.setattr("app.authentication.jwt_middleware.is_jti_revoked", AsyncMock(return_value=False))
    
    res = await mw.dispatch(req, lambda r: "ok")
    assert res.status_code == 403
    import json
    assert "Access Denied" in json.loads(res.body)["detail"]