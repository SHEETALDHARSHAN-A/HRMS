import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from types import SimpleNamespace
import uuid
from fastapi import HTTPException, status

from app.services.job_post.job_post_management_service import JobPostManagementService


@pytest.mark.asyncio
async def test_hard_delete_job_not_found(monkeypatch):
    db = AsyncMock()
    monkeypatch.setattr("app.services.job_post.job_post_management_service.get_job_details_by_id", AsyncMock(return_value=None))
    svc = JobPostManagementService(db)
    with pytest.raises(HTTPException) as exc:
        await svc.hard_delete_job(uuid.UUID(int=1))
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_hard_delete_job_success(monkeypatch):
    db = AsyncMock()
    # get_job_details_by_id returns non-null
    monkeypatch.setattr("app.services.job_post.job_post_management_service.get_job_details_by_id", AsyncMock(return_value={"id": "j1"}))

    # db.execute should return objects with fetchall for profile ids
    res_profile_ids = MagicMock()
    res_profile_ids.fetchall.return_value = []
    # db.execute should also return a result for the final delete with rowcount
    final_delete_res = SimpleNamespace(rowcount=1)
    # Prepare execute side effects: when called for SELECT, return res_profile_ids, final delete return final_delete_res
    async def exec_side_effect(statement, *args, **kwargs):
        # str(statement) can contain SQL; check it as string
        if "SELECT id FROM profiles" in str(statement):
            return res_profile_ids
        # For delete JobDetails return final_delete_res
        return final_delete_res

    db.execute.side_effect = exec_side_effect
    svc = JobPostManagementService(db)
    result = await svc.hard_delete_job(uuid.UUID(int=1))
    assert result["status"] == "permanently_deleted"


@pytest.mark.asyncio
async def test_hard_delete_jobs_batch_empty(monkeypatch):
    db = AsyncMock()
    svc = JobPostManagementService(db)
    with pytest.raises(HTTPException) as exc:
        await svc.hard_delete_jobs_batch([])
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_hard_delete_jobs_batch_no_deleted(monkeypatch):
    db = AsyncMock()
    # Setup db.execute for selects/fetches
    # return no round ids and no profile ids
    class FakeRes:
        def fetchall(self):
            return []
    fake_res = FakeRes()
    # final delete result has rowcount 0
    final_delete_res = SimpleNamespace(rowcount=0)
    async def exec_side_effect(statement, *args, **kwargs):
        stmt_str = str(statement).lower()
        if "select id from profiles" in stmt_str:
            return fake_res
        if "select" in stmt_str:
            return fake_res
        return final_delete_res

    db.execute.side_effect = exec_side_effect
    svc = JobPostManagementService(db)
    with pytest.raises(HTTPException) as exc:
        await svc.hard_delete_jobs_batch([uuid.UUID(int=1)])
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_hard_delete_jobs_batch_success(monkeypatch):
    db = AsyncMock()
    # set up: final delete rowcount > 0
    final_delete_res = SimpleNamespace(rowcount=2)
    # select returns empty lists for fetchall
    class FakeRes:
        def fetchall(self):
            return []
    async def exec_side_effect(statement, *args, **kwargs):
        # return final_delete_res for delete JobDetails
        if "DELETE FROM profiles" in str(statement):
            return FakeRes()
        # final delete delete JobDetails
        if "DELETE FROM job_details" in str(statement):
            return final_delete_res
        # default
        return FakeRes()

    db.execute.side_effect = exec_side_effect
    svc = JobPostManagementService(db)
    result = await svc.hard_delete_jobs_batch([uuid.UUID(int=1), uuid.UUID(int=2)])
    assert result.get("deleted_count") == 2
