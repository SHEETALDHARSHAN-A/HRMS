import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from fastapi import status

from app.controllers.job_post_controller import get_public_job_by_id_controller, toggle_job_status_controller


@pytest.mark.asyncio
@patch("app.controllers.job_post_controller.JobPostReader")
async def test_get_public_job_by_id_controller_inactive(MockJobPostReader):
    reader = MockJobPostReader.return_value
    reader.get_job.return_value = {"is_active": False}

    res = await get_public_job_by_id_controller("some-id")
    assert isinstance(res, dict)
    assert res.get("status_code") == 404


@pytest.mark.asyncio
@patch("app.controllers.job_post_controller.JobPostReader")
@patch("app.controllers.job_post_controller.UpdateJobPost")
async def test_toggle_job_status_permission_denied(MockUpdateJobPost, MockJobPostReader):
    reader = MockJobPostReader.return_value
    reader.get_job.return_value = {"user_id": "owner", "job_id": "jid", "is_active": True}

    # no user in request -> permission denied
    res = await toggle_job_status_controller(job_id="jid", is_active=False, request=None)
    assert isinstance(res, dict)
    assert res.get("status_code") == 403 or res.get("status_code") == 400 or res.get("success") is False