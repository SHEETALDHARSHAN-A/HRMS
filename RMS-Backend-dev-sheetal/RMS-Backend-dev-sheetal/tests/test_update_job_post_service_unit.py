import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from fastapi import status

from app.services.job_post.update_jd.update_job_post import UpdateJobPost


@pytest.mark.asyncio
async def test_update_job_post_min_greater_than_max_returns_422():
    # Use a simple namespace to simulate partial payload
    job_details = SimpleNamespace(minimum_experience=5, maximum_experience=2)
    svc = UpdateJobPost(db=AsyncMock())

    res = await svc.update_job_post(job_details, job_id=None)

    assert isinstance(res, dict)
    assert res.get("status_code") == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert res.get("success") is False


@pytest.mark.asyncio
async def test_update_job_post_repository_value_error_returns_400():
    from app.schemas.update_jd_request import UpdateJdRequest, SkillSchema

    payload = UpdateJdRequest(
        job_title="T",
        job_description="d",
        description_sections=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till="2026-01-01T00:00:00",
        job_location="Remote",
        skills_required=[SkillSchema(skill="Python", weightage=5)],
        interview_rounds=None,
    )

    mock_db = AsyncMock()
    svc = UpdateJobPost(db=mock_db)

    with patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details") as mock_upsert:
        mock_upsert.side_effect = ValueError("creator missing")
        res = await svc.update_job_post(payload, job_id=None, creator_id="creator-1")

    assert isinstance(res, dict)
    assert res.get("status_code") == status.HTTP_400_BAD_REQUEST
    assert res.get("success") is False


@pytest.mark.asyncio
async def test_update_job_post_create_success_returns_job_payload():
    from app.schemas.update_jd_request import UpdateJdRequest, SkillSchema

    payload = UpdateJdRequest(
        job_title="T",
        job_description="d",
        description_sections=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till="2026-01-01T00:00:00",
        job_location="Remote",
        skills_required=[SkillSchema(skill="Python", weightage=5)],
        interview_rounds=None,
    )

    mock_db = AsyncMock()
    svc = UpdateJobPost(db=mock_db)

    # Create a fake DB-returned object that the serializer can process
    fake_updated = SimpleNamespace(**{"job_id": "abc", "job_title": "T", "minimum_experience": 0, "maximum_experience": 0, "user_id": "u1"})

    with patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", return_value=fake_updated):
        res = await svc.update_job_post(payload, job_id=None, creator_id="creator-1")

    assert isinstance(res, dict)
    assert res.get("success") is True
    assert res.get("job_details") is not None