import json
import pytest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from fastapi import status

from app.controllers.job_post_controller import (
    get_job_by_id_controller,
    toggle_job_status_controller,
    delete_job_post_controller,
    delete_job_posts_batch_controller,
    candidate_stats_controller,
    get_my_agent_jobs_controller,
)


@pytest.mark.asyncio
async def test_get_job_by_id_controller_invalid_uuid():
    # Should return a 400 for invalid UUID
    res = await get_job_by_id_controller(job_id="not-a-uuid", request=None)
    assert isinstance(res, dict) or hasattr(res, 'get')
    assert res.get("status_code") == status.HTTP_400_BAD_REQUEST
    assert res.get("success") is False


@pytest.mark.asyncio
async def test_toggle_job_status_controller_repository_fallback(monkeypatch):
    # Simulate UpdateJobPost not returning JSON-like result, forcing repository fallback
    mock_db = AsyncMock()
    with patch("app.controllers.job_post_controller.get_db") as mock_get_db:
        mock_get_db.return_value.__aiter__.return_value = [mock_db]
        # Reader returns job payload for permission check
        with patch("app.controllers.job_post_controller.JobPostReader") as MockReader:
            reader_instance = MockReader.return_value
            reader_instance.get_job.return_value = {"user_id": "u1", "job_id": "j1", "is_active": True}
            # UpdateJobPost.toggle_status returns None so repository path taken
            class FakeUpdate:
                def __init__(self, db):
                    pass
                def toggle_status(self, job_id, is_active):
                    return None

            monkeypatch.setattr("app.controllers.job_post_controller.UpdateJobPost", FakeUpdate)

            # Patch repository set_job_active_status to return True
            async def fake_set_job_active_status(db, job_id, is_active):
                return True
            monkeypatch.setattr("app.controllers.job_post_controller.set_job_active_status", fake_set_job_active_status)

            # Call controller with current user in request state
            request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1", "sub": "u1"}))
            res = await toggle_job_status_controller(job_id="j1", is_active=False, request=request)
            # Expect a success dict
            assert isinstance(res, dict)
            assert res.get("success") is True


@pytest.mark.asyncio
async def test_delete_job_post_controller_permission_denied(monkeypatch):
    mock_db = AsyncMock()
    with patch("app.controllers.job_post_controller.get_db") as mock_get_db:
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        with patch("app.controllers.job_post_controller.JobPostReader") as MockReader:
            reader_instance = MockReader.return_value
            # Job owned by someone else
            reader_instance.get_job.return_value = {"user_id": "other", "job_id": "j1"}

            # Request user is 'u1'
            request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1", "sub": "u1"}))
            res = await delete_job_post_controller(job_id="j1", request=request)

            assert isinstance(res, dict)
            assert res.get("success") is False
            assert res.get("status_code") == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_job_posts_batch_controller_invalid_and_unauthorized(monkeypatch):
    mock_db = AsyncMock()
    with patch("app.controllers.job_post_controller.get_db") as mock_get_db:
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # Mock JobPostReader listing behavior (one invalid id -> None, one unauthorized)
        with patch("app.controllers.job_post_controller.JobPostReader") as MockReader:
            reader_instance = MockReader.return_value
            # First id -> None (invalid), second id -> not owned by user
            async def get_job_side_effect(job_id=None):
                if job_id == "invalid":
                    return None
                return {"user_id": "other", "job_id": job_id}
            reader_instance.get_job.side_effect = get_job_side_effect

            # Request user is 'u1' (non-super admin)
            request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1", "sub": "u1", "role": "USER"}))
            res = await delete_job_posts_batch_controller(job_ids=["invalid", "other-id"], request=request)
            assert isinstance(res, dict)
            # invalid ids should cause 400
            assert res.get("success") is False
            assert res.get("status_code") == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_candidate_stats_controller_success(monkeypatch):
    mock_db = AsyncMock()
    with patch("app.controllers.job_post_controller.get_db") as mock_get_db:
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # Patch ProfileRepository in its module (it's imported inside the function)
        class FakeRepo:
            def __init__(self, db):
                pass
            async def count_by_status(self, job_id, status="applied"):
                return 5 if status == "applied" else 1
        monkeypatch.setattr("app.db.repository.profile_repository.ProfileRepository", FakeRepo)

        res = await candidate_stats_controller(job_id="123e4567-e89b-12d3-a456-426614174000")
        assert isinstance(res, dict)
        assert res.get("success") is True
        data = res.get("data")
        assert data and data.get("profile_counts") and data["profile_counts"]["applied"] == 5


@pytest.mark.asyncio
async def test_get_my_agent_jobs_controller_success(monkeypatch):
    mock_db = AsyncMock()
    with patch("app.controllers.job_post_controller.get_db") as mock_get_db:
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # mock get_agent_jobs_by_user_id to return ORM objects with agent_configs attribute
        class AgentConfig(SimpleNamespace):
            pass

        job_orm = SimpleNamespace(
            id="job1",
            job_id="job1",
            agent_configs=[AgentConfig(id="ac1", job_id="job1", round_list_id="r1", round_name="Round 1", round_focus="focus", persona="persona", key_skills=[], custom_questions=[], forbidden_topics=[], interview_mode="agent", interview_time=30, interviewer_id=None)]
        )

        async def fake_get_agent_jobs_by_user_id(db, user_id):
            return [job_orm]
        monkeypatch.setattr("app.controllers.job_post_controller.get_agent_jobs_by_user_id", fake_get_agent_jobs_by_user_id)

        request = SimpleNamespace(state=SimpleNamespace(user={"user_id": "u1", "sub": "u1"}))
        res = await get_my_agent_jobs_controller(request=request)
        # Controller may return JSONResponse or dict; normalize
        if hasattr(res, 'status_code'):
            assert res.status_code == status.HTTP_200_OK
            res_json = json.loads(res.body)
        else:
            assert res.get("success") is True
            res_json = res
        jobs = res_json.get("data", {}).get("jobs")
        assert isinstance(jobs, list) and len(jobs) == 1
        assert "agentRounds" in jobs[0]
