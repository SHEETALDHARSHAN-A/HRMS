import importlib
import sys
import inspect
import types
import asyncio

import pytest


def _reload_controller_with_missing_target(monkeypatch):
    """Remove target module so controller import will raise and trigger fallback."""
    # Ensure the target module path is not importable
    target = 'app.services.job_post.get_job_post'
    # Remove any cached submodules
    for name in list(sys.modules.keys()):
        if name == target or name.startswith(target + '.'):
            sys.modules.pop(name, None)

    # Also ensure the parent package exists so import will attempt and fail
    # If the module file does not exist on disk, import will raise ImportError.

    # Remove controller from cache so reload will re-execute import-time code
    mod_name = 'app.controllers.job_post_controller'
    sys.modules.pop(mod_name, None)

    # Now import the controller afresh
    return importlib.import_module(mod_name)


def _reload_controller_with_stub_target(monkeypatch):
    """Insert a stub module exporting GetJobDetails and reload controller."""
    target = 'app.services.job_post.get_job_post'

    # Create a dummy module that defines GetJobDetails
    stub = types.ModuleType(target)

    class DummyGetJobDetails:
        def __init__(self, db):
            self.db = db

        def fetch_full_job_details(self, job_id: str):
            return {'id': job_id, 'title': 'Dummy'}

    stub.GetJobDetails = DummyGetJobDetails

    # Insert into sys.modules so the controller import succeeds
    sys.modules[target] = stub

    # Remove controller from cache so it will import fresh
    mod_name = 'app.controllers.job_post_controller'
    sys.modules.pop(mod_name, None)

    return importlib.import_module(mod_name)


def test_import_fallback_defines_async_fetch(monkeypatch):
    """When the target import is missing, controller should expose an async fallback fetch."""
    # Reload controller with missing target to force the except branch
    mod = _reload_controller_with_missing_target(monkeypatch)

    # The controller should define GetJobPost
    assert hasattr(mod, 'GetJobPost')

    GetJobPost = mod.GetJobPost

    inst = GetJobPost(db=None)

    # In the fallback path (as shown in the codebase) fetch_full_job_details is async
    fetch = getattr(inst, 'fetch_full_job_details', None)
    assert fetch is not None
    # It should be awaitable / coroutine function
    assert inspect.iscoroutinefunction(fetch) or asyncio.iscoroutine(fetch)


def test_import_success_uses_stub_class(monkeypatch):
    """When the target module provides GetJobDetails, controller should use it (synchronous fetch)."""
    mod = _reload_controller_with_stub_target(monkeypatch)

    assert hasattr(mod, 'GetJobPost')
    GetJobPost = mod.GetJobPost

    inst = GetJobPost(db_session=None)

    fetch = getattr(inst, 'fetch_full_job_details', None)
    assert fetch is not None

    # For our stub, fetch_full_job_details is synchronous and returns a dict
    result = fetch('job-123')
    assert result == {'id': 'job-123', 'title': 'Dummy'}


def test_dependency_providers_return_expected_types():
    """Test simple dependency provider callables defined in controller module."""
    mod_name = 'app.controllers.job_post_controller'
    mod = importlib.import_module(mod_name)

    # Test get_analyze_jd_service returns an object (class type may differ)
    if hasattr(mod, 'get_analyze_jd_service'):
        svc = mod.get_analyze_jd_service()
        assert svc is not None

    # Test get_job_post_uploader exists and returns UploadJobPost when given a fake redis client
    if hasattr(mod, 'get_job_post_uploader'):
        class DummyRedis:
            pass

        uploader = mod.get_job_post_uploader(redis_client=DummyRedis())
        # We don't assert concrete type, just that it returns an object exposing expected attribute
        assert uploader is not None


import builtins


@pytest.mark.asyncio
async def test_forced_importerror_triggers_async_fallback(monkeypatch):
    """Force ImportError for the target module during controller import to hit except fallback."""
    target_name = 'app.services.job_post.get_job_post'

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Raise ImportError only for the specific target module import
        if name == target_name or name.startswith(target_name + '.'):
            raise ImportError('forced for test')
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', fake_import)

    # Ensure the controller is re-imported freshly
    mod_name = 'app.controllers.job_post_controller'
    sys.modules.pop(mod_name, None)

    mod = importlib.import_module(mod_name)

    # The fallback GetJobPost should be defined and its fetch_full_job_details should be async
    assert hasattr(mod, 'GetJobPost')
    inst = mod.GetJobPost(db=None)
    fetch = getattr(inst, 'fetch_full_job_details')
    assert inspect.iscoroutinefunction(fetch)

    # Patch JobPostReader to avoid hitting repository code; return a plain dict
    class DummyReader:
        def __init__(self, db):
            self.db = db

        def get_job(self, job_id: str):
            return {'id': job_id}

    monkeypatch.setattr(mod, 'JobPostReader', DummyReader)

    result = await inst.fetch_full_job_details('job-xyz')
    assert result == {'id': 'job-xyz'}
