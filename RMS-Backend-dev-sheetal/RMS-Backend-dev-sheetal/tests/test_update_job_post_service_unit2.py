import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from app.services.job_post.update_jd.update_job_post import UpdateJobPost
from datetime import datetime


@pytest.mark.asyncio
async def test_update_job_post_update_path_success():
    mock_db = AsyncMock()
    svc = UpdateJobPost(db=mock_db)

    existing = SimpleNamespace(__dict__={'job_id':'jid','user_id':'u1'}, user_id='u1')
    # patch get_job_details_by_id to return existing_job
    with patch("app.services.job_post.update_jd.update_job_post.get_job_details_by_id", return_value=existing):
        fake_updated = SimpleNamespace(**{"job_id": "jid", "job_title": "Updated", "user_id": "u1"})
        with patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", return_value=fake_updated):
            payload = SimpleNamespace(
                model_dump=lambda **kwargs: {"job_title": "Updated"},
                model_fields_set=set(),
                skills_required=None,
                description_sections=None,
                interview_rounds=None,
                job_location=None,
                job_state=None,
                job_country=None,
                is_agent_interview=False,
                interview_type=None,
            )
            res = await svc.update_job_post(payload, job_id="jid", creator_id="u1")

    assert isinstance(res, dict)
    assert res.get("success") is True
    assert res.get("job_details") is not None


@pytest.mark.asyncio
async def test_update_job_post_upsert_returns_none_causes_500():
    mock_db = AsyncMock()
    svc = UpdateJobPost(db=mock_db)

    with patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", return_value=None):
        payload = SimpleNamespace(model_dump=lambda **kwargs: {}, model_fields_set=set())
        res = await svc.update_job_post(payload, job_id=None, creator_id="u1")

    assert isinstance(res, dict)
    assert res.get("status_code") == 500
    assert res.get("success") is False
