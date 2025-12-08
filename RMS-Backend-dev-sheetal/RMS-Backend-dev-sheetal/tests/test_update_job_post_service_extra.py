import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.job_post.update_jd.update_job_post import UpdateJobPost
from app.schemas.update_jd_request import UpdateJdRequest
from datetime import datetime, timedelta, timezone
from fastapi import status


@pytest.mark.asyncio
async def test_update_job_post_min_exp_validation():
    svc = UpdateJobPost(db=AsyncMock())
    # Pydantic will validate and raise during instantiation; to exercise the
    # service's internal validation branch, pass a simple object that only has
    # the attributes required for the min/max check.
    class FakeJobDetails:
        def __init__(self):
            self.minimum_experience = 5
            self.maximum_experience = 3

    req = FakeJobDetails()
    res = await svc.update_job_post(req, job_id=None, creator_id=None)
    assert res['success'] is False
    assert res['status_code'] == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_job_post_create_missing_creator_returns_401(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    # Provide a valid request object with required fields but no user_id
    req = UpdateJdRequest(
        job_title='SWE',
        job_description='Software Engineer Role',
        description_sections=[{"title": "Context", "content": "Work as part of the team."}],
        active_till=datetime.now(timezone.utc) + timedelta(days=7),
        skills_required=[{"skill": "python", "weightage": 5}],
        job_location='Remote'
    )
    # No creator_id and no user_id in incoming fields -> should return 401
    res = await svc.update_job_post(req, job_id=None, creator_id=None)
    assert res['status_code'] == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_update_job_post_create_success(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    req = UpdateJdRequest(
        job_title='SWE',
        job_description='Software Engineer Role',
        description_sections=[{"title": "Context", "content": "Work as part of the team."}],
        active_till=datetime.now(timezone.utc) + timedelta(days=7),
        skills_required=[{"skill": "python", "weightage": 5}],
        job_location='Remote'
    )
    # Provide creator_id so job creation doesn't raise
    # Patch update_or_create_job_details to return an object
    job_obj = MagicMock()
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.update_or_create_job_details', AsyncMock(return_value=job_obj))
    # Patch serialize_job_details
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.serialize_job_details', lambda j: {'job_title': 'SWE'})
    res = await svc.update_job_post(req, job_id=None, creator_id='u1')
    assert res['success'] is True
    assert res['job_details']['job_title'] == 'SWE'


@pytest.mark.asyncio
async def test_update_job_post_update_success(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    req = UpdateJdRequest(
        job_title='SWE',
        job_description='Software Engineer Role',
        description_sections=[{"title": "Context", "content": "Work as part of the team."}],
        active_till=datetime.now(timezone.utc) + timedelta(days=7),
        skills_required=[{"skill": "python", "weightage": 5}],
        job_location='Remote'
    )
    job_obj = MagicMock()
    # Simulate get_job_details_by_id returns existing job
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.get_job_details_by_id', AsyncMock(return_value=job_obj))
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.update_or_create_job_details', AsyncMock(return_value=job_obj))
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.serialize_job_details', lambda j: {'job_title': 'SWE'})
    res = await svc.update_job_post(req, job_id='11111111-1111-1111-1111-111111111111', creator_id=None)
    assert res['success'] is True


@pytest.mark.asyncio
async def test_toggle_status_invalid_job(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    # set_job_active_status is imported from the repository inside the method
    monkeypatch.setattr('app.db.repository.job_post_repository.set_job_active_status', AsyncMock(return_value=None))
    res = await svc.toggle_status('11111111-1111-1111-1111-111111111111', True)
    assert res['success'] is False
    assert res['status_code'] == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_toggle_status_success(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    job_obj = MagicMock()
    job_obj.is_active = True
    monkeypatch.setattr('app.db.repository.job_post_repository.set_job_active_status', AsyncMock(return_value=job_obj))
    monkeypatch.setattr('app.services.job_post.update_jd.update_job_post.serialize_job_details', lambda j: {'job_title': 'SWE', 'is_active': True})
    res = await svc.toggle_status('11111111-1111-1111-1111-111111111111', True)
    assert res['success'] is True
    assert res['data']['job_details']['is_active'] == True


@pytest.mark.asyncio
async def test_delete_job_post_invalid(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    monkeypatch.setattr('app.db.repository.job_post_repository.hard_delete_job_by_id', AsyncMock(return_value=False))
    res = await svc.delete_job_post('11111111-1111-1111-1111-111111111111')
    assert res['success'] is False
    assert res['status_code'] == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_job_post_success(monkeypatch):
    db = AsyncMock()
    svc = UpdateJobPost(db=db)
    monkeypatch.setattr('app.db.repository.job_post_repository.hard_delete_job_by_id', AsyncMock(return_value=True))
    res = await svc.delete_job_post('11111111-1111-1111-1111-111111111111')
    assert res['success'] is True
    assert res['data']['deleted'] is True
