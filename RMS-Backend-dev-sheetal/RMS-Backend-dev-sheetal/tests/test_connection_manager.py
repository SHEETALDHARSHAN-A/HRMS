import importlib
import os
import pytest


def test_base_is_dummy_when_testing_env(monkeypatch):
    """When TESTING env var is set, module should expose _DummyBase and Base should be that."""
    monkeypatch.setenv("TESTING", "1")
    import app.db.connection_manager as cm
    importlib.reload(cm)

    assert hasattr(cm, "_DummyBase"), "_DummyBase should be defined under TESTING"
    assert cm.Base is cm._DummyBase


@pytest.mark.asyncio
async def test_get_db_yields_session(monkeypatch):
    """The async generator `get_db` should yield the session object from AsyncSessionLocal."""
    import app.db.connection_manager as cm

    mock_session = object()

    class AsyncCtx:
        def __init__(self, obj):
            self.obj = obj

        async def __aenter__(self):
            return self.obj

        async def __aexit__(self, exc_type, exc, tb):
            return False

    # Replace the AsyncSessionLocal factory with one that yields our mock_session
    monkeypatch.setattr(cm, "AsyncSessionLocal", lambda: AsyncCtx(mock_session))

    # Iterate the async generator once and verify the yielded session is our mock
    async for sess in cm.get_db():
        assert sess is mock_session
        break


def test_base_is_declarative_when_not_testing(monkeypatch):
    """When TESTING is not set, Base should be a SQLAlchemy declarative base (has metadata)."""
    monkeypatch.delenv("TESTING", raising=False)
    import app.db.connection_manager as cm
    importlib.reload(cm)

    # declarative_base() produced object should have a 'metadata' attribute
    assert hasattr(cm.Base, "metadata")
