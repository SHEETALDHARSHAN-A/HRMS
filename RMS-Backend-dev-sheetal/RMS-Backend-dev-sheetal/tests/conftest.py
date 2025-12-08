import json
import os
import sys

os.environ.setdefault("app_base_url", "http://testserver")
os.environ.setdefault("frontend_url", "http://testserver")
os.environ.setdefault("frontend_base_url", "http://testserver")
os.environ.setdefault("redis_host", "localhost")
os.environ.setdefault("redis_port", "6379")
os.environ.setdefault("redis_db", "0")
os.environ.setdefault("openai_api_key", "x")
os.environ.setdefault("openai_model", "gpt-test")
os.environ.setdefault("temperature", "0.0")
os.environ.setdefault("openai_cache", "false")
os.environ.setdefault("db_name", "testdb")
os.environ.setdefault("db_user", "test")
os.environ.setdefault("db_password", "x")
os.environ.setdefault("db_host", "localhost")
os.environ.setdefault("db_port", "5432")
os.environ.setdefault("db_pool_size", "1")
os.environ.setdefault("db_max_over_flow", "1")
os.environ.setdefault("otp_expire_seconds", "300")
os.environ.setdefault("smtp_server", "smtp")
os.environ.setdefault("smtp_port", "25")
os.environ.setdefault("smtp_username", "x")
os.environ.setdefault("smtp_password", "x")
os.environ.setdefault("samesite", "Lax")
os.environ.setdefault("secure", "false")
os.environ.setdefault("allow_origins", "[]")
os.environ.setdefault("allow_domains", "[]")
os.environ.setdefault("secret_key", "secret")
os.environ.setdefault("algorithm", "HS256")
os.environ.setdefault("access_token_expire_minutes", "60")
os.environ.setdefault("access_refresh_token_expire_hours", "24")
os.environ.setdefault("invite_expire_minutes", "60")
os.environ.setdefault("invite_expire_seconds", "3600")
os.environ.setdefault("remember_me_expire_days", "7")
os.environ.setdefault("report_mail", "a@b.c")
os.environ.setdefault("default_tenant_id", "t")
os.environ.setdefault("link_expiration", "3600")
import pytest
from unittest.mock import AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.api.v1.authentication_routes import auth_router, admin_router
from app.api.v1.agent_config_routes import agent_config_router
from app.api.v1.career_routes import career_router
import app.controllers.authentication_controller as auth_ctrl
from app.db.connection_manager import get_db
from app.db.redis_manager import get_redis_client


async def _fake_get_db():
    mock_db = AsyncMock()
    try:
        yield mock_db
    finally:
        pass


async def _fake_get_redis_client():
    mock_cache = AsyncMock()
    try:
        yield mock_cache
    finally:
        pass


@pytest.fixture(scope="session")
def test_app():
    """Create a FastAPI app for tests with common routers and overrides."""
    app = FastAPI()
    app.include_router(auth_router, prefix="/v1")
    app.include_router(admin_router, prefix="/v1")
    app.include_router(agent_config_router, prefix="/v1")
    app.include_router(career_router, prefix="/v1")

    # Middleware to inject a test user via `x-test-user` header (JSON)
    @app.middleware("http")
    async def _inject_test_user(request, call_next):
        test_user_json = request.headers.get("x-test-user")
        if test_user_json:
            try:
                request.state.user = json.loads(test_user_json)
            except Exception:
                request.state.user = None
        else:
            request.state.user = None
        return await call_next(request)

    # Dependency overrides to avoid real DB/cache during unit tests
    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_redis_client] = _fake_get_redis_client

    # Ensure redirect targets resolve to the TestClient server
    try:
        auth_ctrl.settings.frontend_url = "http://testserver"
    except Exception:
        # If settings is not present in the module, ignore
        pass

    # Add lightweight dummy endpoints to catch frontend redirects
    @app.get("/verification/processing")
    def _dummy_verification_processing():
        return {"success": True}

    @app.get("/auth")
    def _dummy_auth_route():
        return {"success": True}

    return app


# In test mode, stub out networky email helpers to avoid external network calls
if os.environ.get("TESTING"):
    try:
        import app.utils.email_utils as _email_utils

        async def _fake_send_email_update_verification_link(*args, **kwargs):
            return True

        # Replace only if present
        if hasattr(_email_utils, 'send_email_update_verification_link'):
            _email_utils.send_email_update_verification_link = _fake_send_email_update_verification_link
        # Also patch service-level aliases that may have been imported earlier
        try:
            import app.services.admin_service.update_admin_service as _uas
            if hasattr(_uas, 'send_email_update_verification_link'):
                _uas.send_email_update_verification_link = _fake_send_email_update_verification_link
        except Exception:
            pass
    except Exception:
        pass


@pytest.fixture(scope="session")
def client(test_app):
    return TestClient(test_app)
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import os
os.environ.setdefault("TESTING", "1")
import pytest
import uuid
from unittest.mock import AsyncMock
from app.config.app_config import AppConfig


@pytest.fixture
def settings():
    return AppConfig()


class FakeDB:
    def __init__(self):
        self.added = []
        self.deleted = []
    def add(self, obj):
        self.added.append(obj)
    async def commit(self):
        return None
    async def refresh(self, obj):
        # simulate DB assigning ids
        if hasattr(obj, 'invitation_id') and obj.invitation_id is None:
            obj.invitation_id = uuid.uuid4()
        return None
    async def delete(self, obj):
        self.deleted.append(obj)
        return None
    async def execute(self, query):
        class Result:
            def scalar_one_or_none(self_inner):
                return None
        return Result()
    async def rollback(self):
        return None


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def fake_cache():
    mock = AsyncMock()
    mock.set = AsyncMock()
    mock.get = AsyncMock()
    mock.delete = AsyncMock()
    mock.exists = AsyncMock()
    mock.ttl = AsyncMock()
    return mock
