import pytest
from unittest.mock import patch
from types import SimpleNamespace
from app.controllers.job_post_controller import get_all_jobs_controller, get_active_jobs_controller


@pytest.mark.asyncio
async def test_get_all_jobs_controller(monkeypatch):
    # Ensure the controller uses a mocked reader and permissions to prevent repo calls
    async def fake_list_all():
        return [{"job_id": "1"}]

    # Patch the job_post_reader functions used by JobPostReader to avoid repository SQL
    from unittest.mock import AsyncMock
    monkeypatch.setattr('app.services.job_post.job_post_reader.get_all_job_details', AsyncMock(return_value=[{"job_id": "1"}]))
    # Ensure permissions filter is a no-op
    from app.controllers import job_post_controller as controller
    monkeypatch.setattr(controller, 'JobPostPermissions', SimpleNamespace(filter_jobs_by_ownership=lambda jobs, user: jobs))

    res = await get_all_jobs_controller(request=None)
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert isinstance(res.get("data"), dict)


@pytest.mark.asyncio
async def test_get_active_jobs_controller(monkeypatch):
    async def fake_list_active():
        return [{"job_id": "1"}]
    from unittest.mock import AsyncMock
    monkeypatch.setattr('app.services.job_post.job_post_reader.get_active_job_details', AsyncMock(return_value=[{"job_id": "1"}]))
    res = await get_active_jobs_controller()
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert isinstance(res.get("data"), dict)
