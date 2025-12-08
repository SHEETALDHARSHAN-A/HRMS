import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.services.job_post.job_post_management_service import JobPostManagementService


class _FakeDelete:
    def __init__(self, target):
        self.target = target

    def where(self, *args, **kwargs):
        return self


@pytest.mark.asyncio
async def test_hard_delete_job_success(fake_db):
    # Mock get_job_details_by_id to return True (job exists)
    with patch("app.services.job_post.job_post_management_service.get_job_details_by_id", AsyncMock(return_value=True)):
        # Patch the module-level `delete` to avoid SQLAlchemy coercion during unit tests
        with patch("app.services.job_post.job_post_management_service.delete", side_effect=lambda t: _FakeDelete(t)):
            # Mock DB execute
            fake_db.execute = AsyncMock()
            fake_db.commit = AsyncMock()

            # Mock the result of profile ID selection
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("profile-1",)]
            fake_db.execute.side_effect = [
                # The delete statements return Result objects usually, but the select returns rows
                MagicMock(), # delete criteria
                MagicMock(), # delete interview rounds
                MagicMock(), # delete round list
                MagicMock(), # delete skills
                MagicMock(), # delete description
                MagicMock(), # delete locations
                mock_result, # SELECT id FROM profiles
                MagicMock(), # delete scheduling
                MagicMock(), # delete curation
                MagicMock(), # delete profiles
                MagicMock(), # delete job details
            ]

            svc = JobPostManagementService(fake_db)
            res = await svc.hard_delete_job(uuid.uuid4())

            assert res["status"] == "permanently_deleted"
            assert fake_db.commit.called

@pytest.mark.asyncio
async def test_hard_delete_job_not_found(fake_db):
    with patch("app.services.job_post.job_post_management_service.get_job_details_by_id", AsyncMock(return_value=None)):
        svc = JobPostManagementService(fake_db)
        with pytest.raises(HTTPException) as exc:
            await svc.hard_delete_job(uuid.uuid4())
        assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_hard_delete_jobs_batch_success(fake_db):
    # Mock DB executes
    fake_db.execute = AsyncMock()
    # Mock returning round IDs
    mock_rounds = MagicMock()
    mock_rounds.fetchall.return_value = [("r1",)]
    
    # Mock returning profile IDs
    mock_profiles = MagicMock()
    mock_profiles.fetchall.return_value = [("p1",)]
    
    # Mock final delete count
    mock_del_res = MagicMock()
    mock_del_res.rowcount = 2
    
    # Setup side effects for sequence of calls
    # Patch delete to avoid SQLAlchemy coercion
    with patch("app.services.job_post.job_post_management_service.delete", side_effect=lambda t: _FakeDelete(t)):
        fake_db.execute.side_effect = [
        MagicMock(), # eval criteria
        mock_rounds, # select rounds
        MagicMock(), # delete interview rounds
        MagicMock(), # delete round list
        MagicMock(), # delete skills
        MagicMock(), # delete desc
        MagicMock(), # delete locs
        mock_profiles, # select profiles
        MagicMock(), # delete scheduling
        MagicMock(), # delete curation
        MagicMock(), # delete profiles
        mock_del_res # delete jobs
    ]
    
        svc = JobPostManagementService(fake_db)
        res = await svc.hard_delete_jobs_batch([uuid.uuid4(), uuid.uuid4()])
    
    assert res["deleted_count"] == 2

@pytest.mark.asyncio
async def test_hard_delete_jobs_batch_none_found(fake_db):
    fake_db.execute = AsyncMock()
    # Mock empty rounds/profiles/delete
    mock_empty = MagicMock()
    mock_empty.fetchall.return_value = []
    mock_del_zero = MagicMock()
    mock_del_zero.rowcount = 0
    
    # We need to provide enough side effects to reach the final delete check
    fake_db.execute.side_effect = [
        MagicMock(), # eval criteria
        mock_empty, # select rounds
        MagicMock(), # delete roundlist
        MagicMock(), # delete jobskills
        MagicMock(), # delete desc
        MagicMock(), # delete locations
        mock_empty,  # select profiles
        MagicMock(), # delete profiles (from _execute_delete)
        mock_del_zero # final delete jobs -> zero rows
    ]

    # Patch delete for batch function as well
    with patch("app.services.job_post.job_post_management_service.delete", side_effect=lambda t: _FakeDelete(t)):
        svc = JobPostManagementService(fake_db)
        with pytest.raises(HTTPException) as exc:
            await svc.hard_delete_jobs_batch([uuid.uuid4()])
        assert exc.value.status_code == 404