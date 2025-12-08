import pytest
import types

import asyncio

from fastapi.responses import JSONResponse

from app.authentication.jwt_middleware import JWTMiddleware


class DummyURL:
    def __init__(self, path):
        self.path = path


class DummyRequest:
    def __init__(self, path='/', method='GET', cookies=None, headers=None, query_params=None, app=None, scope=None):
        self.url = DummyURL(path)
        self.method = method
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.app = app
        import types as _types
        self.state = _types.SimpleNamespace()
        self.scope = scope or {}


@pytest.mark.asyncio
async def test_options_short_circuit_and_excluded_route():
    mw = JWTMiddleware(app=None, excluded_routes=['/health'])

    async def call_next(req):
        return "NEXT"

    # OPTIONS should short-circuit to call_next
    req_opt = DummyRequest(path='/', method='OPTIONS')
    res_opt = await mw.dispatch(req_opt, call_next)
    assert res_opt == "NEXT"

    # Excluded route should also short-circuit
    req_ex = DummyRequest(path='/health', method='GET')
    res_ex = await mw.dispatch(req_ex, call_next)
    assert res_ex == "NEXT"


@pytest.mark.asyncio
async def test_missing_jwt_settings_returns_500(monkeypatch):
    # Provide a token but app state missing jwt settings
    fake_app = types.SimpleNamespace(state=types.SimpleNamespace(jwt_secret_key=None, jwt_algorithm=None))
    req = DummyRequest(path='/v1/some', method='GET', cookies={'access_token': 't'}, app=fake_app)

    async def call_next(req):
        return "NEXT"

    mw = JWTMiddleware(app=None)

    # Patch RedisManager.get_client to return a dummy client
    from app.authentication import jwt_middleware as jm_mod
    monkeypatch.setattr(jm_mod, 'RedisManager', types.SimpleNamespace(get_client=lambda: object()))

    res = await mw.dispatch(req, call_next)
    assert isinstance(res, JSONResponse)
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_revoked_jti_returns_401(monkeypatch):
    fake_app = types.SimpleNamespace(state=types.SimpleNamespace(jwt_secret_key='s', jwt_algorithm='HS256'))
    req = DummyRequest(path='/v1/protected', method='GET', cookies={'access_token': 't'}, app=fake_app)

    async def call_next(req):
        return "NEXT"

    mw = JWTMiddleware(app=None)

    # Patch RedisManager.get_client
    from app.authentication import jwt_middleware as jm_mod
    monkeypatch.setattr(jm_mod, 'RedisManager', types.SimpleNamespace(get_client=lambda: object()))

    # Patch jwt.decode to return payload with jti
    monkeypatch.setattr(jm_mod, 'jwt', types.SimpleNamespace(decode=lambda token, secret, algorithms=None: {"jti": "j1", "role": "ADMIN"}))

    # Patch is_jti_revoked to True (async)
    async def _revoked(jti, r):
        return True
    monkeypatch.setattr(jm_mod, 'is_jti_revoked', _revoked)

    res = await mw.dispatch(req, call_next)
    assert isinstance(res, JSONResponse)
    assert res.status_code == 401
