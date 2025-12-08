import pytest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from app.services.job_post.update_jd.update_job_post import UpdateJobPost
from fastapi import status


class FakeDB:
    pass


def make_fake_job_details(**kwargs):
    # Minimal fake object that provides model_dump and attributes used by service
    class JD:
        def __init__(self, **kw):
            # sensible defaults used by service
            defaults = {
                'job_title': None,
                'minimum_experience': None,
                'maximum_experience': None,
                'job_location': None,
                'job_state': None,
                'job_country': None,
                'is_agent_interview': False,
                'interview_type': None,
                'interview_rounds': None,
                'no_of_openings': None,
            }
            defaults.update(kw)
            self.__dict__.update(defaults)
            # model_fields_set mimics pydantic set of fields present
            self.model_fields_set = set(getattr(self, 'model_fields_set', []))

        def model_dump(self, exclude_unset=False, exclude=None):
            data = {}
            # include any scalar attributes except callables
            for k, v in self.__dict__.items():
                if not k.startswith("_") and not callable(v):
                    data[k] = v
            # remove excluded keys
            if exclude:
                for key in exclude:
                    data.pop(key, None)
            return data

    return JD(**kwargs)


@patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", new_callable=AsyncMock)
@patch("app.services.job_post.update_jd.update_job_post.get_job_details_by_id", new_callable=AsyncMock)
@patch("app.services.job_post.update_jd.update_job_post.serialize_job_details")
@pytest.mark.asyncio
async def test_update_action_merges_existing_and_preserves_user(mock_serialize, mock_get_job, mock_update_or_create):
    db = FakeDB()
    svc = UpdateJobPost(db)

    # existing job returned by repository
    existing = SimpleNamespace(user_id="existing_user", some_field="keep_me")
    # Ensure __dict__ contains keys that service expects
    existing.__dict__.update({"_sa_instance_state": None})

    mock_get_job.return_value = existing

    # When repository called, return an object that serialize_job_details will convert
    updated_obj = SimpleNamespace(job_title="T", user_id="existing_user")
    mock_update_or_create.return_value = updated_obj

    mock_serialize.return_value = {"job_title": "T", "user_id": "existing_user"}

    jd = make_fake_job_details(job_title="T", job_location=None, is_agent_interview=False)

    res = await svc.update_job_post(job_details=jd, job_id="some-id", creator_id=None)

    assert res["success"] is True
    assert res["job_details"]["job_title"] == "T"
    # user_id is stripped from payload by service
    assert "user_id" not in res["job_details"]


@patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_create_missing_creator_returns_401(mock_update_or_create):
    db = FakeDB()
    svc = UpdateJobPost(db)

    jd = make_fake_job_details(job_title="New Job")

    res = await svc.update_job_post(job_details=jd, job_id=None, creator_id=None)

    assert res["success"] is False
    assert res["status_code"] == status.HTTP_401_UNAUTHORIZED


@patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", new_callable=AsyncMock)
@patch("app.services.job_post.update_jd.update_job_post.get_job_details_by_id", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_update_repo_returns_none_results_in_500(mock_get_job, mock_update_or_create):
    db = FakeDB()
    svc = UpdateJobPost(db)

    # simulate existing job
    existing = SimpleNamespace(user_id="u1")
    existing.__dict__.update({"_sa_instance_state": None})
    mock_get_job.return_value = existing

    # repository returns None to indicate failure
    mock_update_or_create.return_value = None

    jd = make_fake_job_details(job_title="T")

    res = await svc.update_job_post(job_details=jd, job_id="id-123", creator_id=None)

    assert res["success"] is False
    assert res["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


@patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_create_repo_value_error_returns_400(mock_update_or_create):
    db = FakeDB()
    svc = UpdateJobPost(db)

    # Make the repository raise ValueError when called during CREATE
    mock_update_or_create.side_effect = ValueError("invalid payload")

    jd = make_fake_job_details(job_title="New Job", user_id="creator-1")

    res = await svc.update_job_post(job_details=jd, job_id=None, creator_id="creator-1")

    assert res["success"] is False
    assert res["status_code"] == status.HTTP_400_BAD_REQUEST
