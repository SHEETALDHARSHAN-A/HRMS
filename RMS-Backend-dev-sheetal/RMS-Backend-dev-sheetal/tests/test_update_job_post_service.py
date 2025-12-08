import asyncio
import uuid
from types import SimpleNamespace
import pytest

import app.services.job_post.update_jd.update_job_post as uj_mod


@pytest.mark.asyncio
async def test_update_job_post_min_greater_than_max_returns_422():
    svc = uj_mod.UpdateJobPost(db=object())
    jd = SimpleNamespace(minimum_experience=5, maximum_experience=2)

    res = await svc.update_job_post(job_details=jd)
    assert res["success"] is False
    assert res.get("status_code") == 422


@pytest.mark.asyncio
async def test_update_job_post_create_missing_creator_returns_401():
    svc = uj_mod.UpdateJobPost(db=object())

    # Create a minimal pydantic-like object with model_dump and attributes
    jd = SimpleNamespace(
        model_dump=lambda **k: {},
        model_fields_set=set(),
        job_location=None,
        skills_required=None,
        description_sections=None,
        interview_rounds=None,
        agent_configs=None,
    )

    res = await svc.update_job_post(job_details=jd, job_id=None, creator_id=None)
    assert res["success"] is False
    assert res.get("status_code") == 401


@pytest.mark.asyncio
async def test_update_job_post_create_repo_value_error_returns_400(monkeypatch):
    svc = uj_mod.UpdateJobPost(db=object())

    jd = SimpleNamespace(
        model_dump=lambda **k: {},
        model_fields_set={"no_of_openings"},
        job_location=None,
        job_state=None,
        job_country=None,
        no_of_openings=1,
        skills_required=None,
        description_sections=None,
        interview_rounds=None,
        agent_configs=None,
    )

    async def fake_upsert(**kwargs):
        raise ValueError("duplicate")

    monkeypatch.setattr(uj_mod, "update_or_create_job_details", fake_upsert)

    res = await svc.update_job_post(job_details=jd, job_id=None, creator_id=str(uuid.uuid4()))
    assert res["success"] is False
    assert res.get("status_code") == 400
    assert "duplicate" in res.get("message")


@pytest.mark.asyncio
async def test_update_job_post_create_success(monkeypatch):
    svc = uj_mod.UpdateJobPost(db=object())

    # Prepare job_details with some fields
    jd = SimpleNamespace(
        model_dump=lambda **k: {"job_title": "T"},
        model_fields_set={"job_title"},
        job_location="Remote",
        job_state=None,
        job_country=None,
        skills_required=[],
        description_sections=None,
        interview_rounds=None,
        agent_configs=None,
    )

    # fake updated job (repo returns an ORM-like object)
    updated_obj = SimpleNamespace(job_id=str(uuid.uuid4()), user_id="u1", job_title="T")

    async def fake_upsert(db, job_id, job_data, **kwargs):
        return updated_obj

    def fake_serialize(obj):
        return {"job_title": obj.job_title, "user_id": obj.user_id}

    monkeypatch.setattr(uj_mod, "update_or_create_job_details", fake_upsert)
    monkeypatch.setattr(uj_mod, "serialize_job_details", fake_serialize)

    res = await svc.update_job_post(job_details=jd, job_id=None, creator_id="creator-1")
    assert res["success"] is True
    assert "job_details" in res and res["job_details"]["job_title"] == "T"
    # user_id must be removed by service
    assert "user_id" not in res["job_details"]


@pytest.mark.asyncio
async def test_toggle_status_success_and_not_found(monkeypatch):
    svc = uj_mod.UpdateJobPost(db=object())

    # Case: not found
    async def fake_set_none(db, job_id, is_active):
        return None

    # patch the repository function which is imported inside the service method
    monkeypatch.setattr(
        "app.db.repository.job_post_repository.set_job_active_status",
        fake_set_none,
    )
    res = await svc.toggle_status(job_id="jid", is_active=False)
    assert res["success"] is False
    assert res.get("status_code") == 400

    # Case: success
    updated_obj = SimpleNamespace(job_id="jid", user_id="u1", is_active=True)

    async def fake_set_ok(db, job_id, is_active):
        return updated_obj

    def fake_serialize(obj):
        return {"job_id": obj.job_id, "user_id": obj.user_id}

    monkeypatch.setattr(
        "app.db.repository.job_post_repository.set_job_active_status",
        fake_set_ok,
    )
    monkeypatch.setattr(uj_mod, "serialize_job_details", fake_serialize)

    res2 = await svc.toggle_status(job_id="jid", is_active=False)
    assert res2["success"] is True
    assert res2["data"]["job_details"]["job_id"] == "jid"
    assert res2["data"]["job_details"]["is_active"] is False


@pytest.mark.asyncio
async def test_delete_job_post_success_and_not_found(monkeypatch):
    svc = uj_mod.UpdateJobPost(db=object())

    async def fake_hard_none(db, job_id):
        return False

    # patch the repository function which is imported inside the service method
    monkeypatch.setattr(
        "app.db.repository.job_post_repository.hard_delete_job_by_id",
        fake_hard_none,
    )
    res = await svc.delete_job_post(job_id="x")
    assert res["success"] is False
    assert res.get("status_code") == 400

    async def fake_hard_ok(db, job_id):
        return True

    monkeypatch.setattr(
        "app.db.repository.job_post_repository.hard_delete_job_by_id",
        fake_hard_ok,
    )
    res2 = await svc.delete_job_post(job_id="x")
    assert res2["success"] is True
    assert res2["data"]["job_id"] == "x"
import pytest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from datetime import datetime

from app.services.job_post.update_jd.update_job_post import UpdateJobPost


class DummySkill:
    def __init__(self, skill, weightage=5):
        self.skill = skill
        self.weightage = weightage


class DummyRound:
    def __init__(self):
        self.level_name = "Technical"
        self.round_order = 1
        self.shortlisting_threshold = 50
        self.rejecting_threshold = 40


@pytest.mark.asyncio
async def test_validation_min_greater_than_max_raises():
    # Use a simple object to trigger the early validation branch
    job_details = SimpleNamespace(minimum_experience=5, maximum_experience=2)
    svc = UpdateJobPost(db=AsyncMock())

    res = await svc.update_job_post(job_details, job_id=None)

    assert isinstance(res, dict)
    assert res.get("status_code") == 422
    assert res.get("success") is False


@pytest.mark.asyncio
async def test_create_without_creator_fails():
    # Build a valid UpdateJdRequest-like object using pydantic schema via dynamic import
    from app.schemas.update_jd_request import UpdateJdRequest, SkillSchema

    payload = UpdateJdRequest(
        job_title="T",
        job_description="d",
        description_sections=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till="2026-01-01T00:00:00",
        job_location=None,
        skills_required=[SkillSchema(skill="Python", weightage=5)],
        interview_rounds=None,
    )

    svc = UpdateJobPost(db=AsyncMock())

    res = await svc.update_job_post(payload, job_id=None, creator_id=None)

    assert isinstance(res, dict)
    assert res.get("status_code") == 401
    assert res.get("success") is False


@pytest.mark.asyncio
async def test_create_success_uses_repository_and_serializer():
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

    # Patch repository upsert and serializer
    with patch("app.services.job_post.update_jd.update_job_post.update_or_create_job_details") as mock_upsert:
        with patch("app.services.job_post.update_jd.update_job_post.serialize_job_details") as mock_serialize:
            # repository returns a fake ORM-like object
            fake_job = SimpleNamespace()
            mock_upsert.return_value = fake_job

            mock_serialize.return_value = {"job_title": "T", "user_id": "u1"}

            res = await svc.update_job_post(payload, job_id=None, creator_id="creator-1")

            assert isinstance(res, dict)
            assert res.get("success") is True
            assert res.get("job_details", {}).get("job_title") == "T"


@pytest.mark.asyncio
async def test_repository_value_error_returns_400():
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
        assert res.get("status_code") == 400
        assert res.get("success") is False
