import pytest
from datetime import datetime, timezone, timedelta

from app.services.job_post.update_jd.update_job_post import UpdateJobPost
from app.schemas.update_jd_request import UpdateJdRequest, SkillSchema


class SimpleObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.mark.asyncio
async def test_min_greater_than_max_early_validation():
    svc = UpdateJobPost(db=None)
    # Use a simple object that has attributes to trigger the early check
    simple = SimpleObj(minimum_experience=5, maximum_experience=2)
    res = await svc.update_job_post(simple, job_id=None, creator_id=None)
    assert res["success"] is False
    assert res.get("status_code") == 422


@pytest.mark.asyncio
async def test_create_missing_creator_returns_401():
    svc = UpdateJobPost(db=None)
    req = UpdateJdRequest(
        job_title="T",
        job_description=None,
        description_sections=None,
        job_location=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till=datetime.now(timezone.utc) + timedelta(days=1),
        skills_required=[SkillSchema(skill="py", weightage=5)],
    )

    res = await svc.update_job_post(req, job_id=None, creator_id=None)
    assert res["success"] is False
    assert res.get("status_code") == 401


@pytest.mark.asyncio
async def test_create_repo_value_error_returns_client_error(monkeypatch):
    svc = UpdateJobPost(db=None)
    req = UpdateJdRequest(
        job_title="T",
        job_description=None,
        description_sections=None,
        job_location=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till=datetime.now(timezone.utc) + timedelta(days=1),
        skills_required=[SkillSchema(skill="py", weightage=5)],
    )

    async def fake_update_or_create_job_details(**kwargs):
        raise ValueError("already exists")

    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.update_or_create_job_details",
        fake_update_or_create_job_details,
    )

    res = await svc.update_job_post(req, job_id=None, creator_id="creator-1")
    assert res["success"] is False
    assert res.get("status_code") == 400


@pytest.mark.asyncio
async def test_create_successful_returns_payload(monkeypatch):
    svc = UpdateJobPost(db=None)
    req = UpdateJdRequest(
        job_title="T",
        job_description=None,
        description_sections=None,
        job_location=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till=datetime.now(timezone.utc) + timedelta(days=1),
        skills_required=[SkillSchema(skill="py", weightage=5)],
    )

    class DummyUpdated:
        def __init__(self, job_id):
            self.job_id = job_id
            self.user_id = "creator-1"

    async def fake_update_or_create_job_details(db, job_id, job_data, **kwargs):
        return DummyUpdated(job_id)

    def fake_serialize_job_details(obj):
        return {"job_id": getattr(obj, "job_id", None), "user_id": getattr(obj, "user_id", None), "job_title": "T"}

    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.update_or_create_job_details",
        fake_update_or_create_job_details,
    )
    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.serialize_job_details",
        fake_serialize_job_details,
    )

    res = await svc.update_job_post(req, job_id=None, creator_id="creator-1")
    assert res["success"] is True
    assert res["job_details"]["job_title"] == "T"
    # user_id should be popped from response
    assert "user_id" not in res["job_details"]


@pytest.mark.asyncio
async def test_update_merges_existing_job(monkeypatch):
    svc = UpdateJobPost(db=None)
    req = UpdateJdRequest(
        job_title="Updated",
        job_description=None,
        description_sections=None,
        job_location=None,
        minimum_experience=0,
        maximum_experience=0,
        no_of_openings=1,
        active_till=datetime.now(timezone.utc) + timedelta(days=1),
        skills_required=[SkillSchema(skill="py", weightage=5)],
    )

    class Existing:
        def __init__(self):
            self.user_id = "orig-user"
            self._sa_instance_state = None

    async def fake_get_job_details_by_id(db, job_id):
        return Existing()

    async def fake_update_or_create_job_details(db, job_id, job_data, **kwargs):
        class Out:
            pass
        out = Out()
        out.job_id = job_id
        out.user_id = job_data.get("user_id")
        return out

    def fake_serialize(obj):
        return {"job_id": obj.job_id, "user_id": obj.user_id}

    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.get_job_details_by_id",
        fake_get_job_details_by_id,
    )
    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.update_or_create_job_details",
        fake_update_or_create_job_details,
    )
    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.serialize_job_details",
        fake_serialize,
    )

    res = await svc.update_job_post(req, job_id="jid-1", creator_id=None)
    assert res["success"] is True
    assert res["job_details"]["job_id"] == "jid-1"


@pytest.mark.asyncio
async def test_toggle_status_not_found(monkeypatch):
    svc = UpdateJobPost(db=None)

    async def fake_set_job_active_status(db, job_id, is_active):
        return False

    monkeypatch.setattr(
        "app.db.repository.job_post_repository.set_job_active_status",
        fake_set_job_active_status,
    )

    res = await svc.toggle_status("jid-x", True)
    assert res["success"] is False
    assert res["status_code"] == 400


@pytest.mark.asyncio
async def test_toggle_status_success(monkeypatch):
    svc = UpdateJobPost(db=None)

    class Updated:
        pass

    updated = Updated()
    updated.job_id = "jid-x"
    updated.user_id = "u"

    async def fake_set_job_active_status(db, job_id, is_active):
        return updated

    def fake_serialize_job_details(obj):
        return {"job_id": obj.job_id, "user_id": obj.user_id}

    monkeypatch.setattr(
        "app.db.repository.job_post_repository.set_job_active_status",
        fake_set_job_active_status,
    )
    monkeypatch.setattr(
        "app.services.job_post.update_jd.update_job_post.serialize_job_details",
        fake_serialize_job_details,
    )

    res = await svc.toggle_status("jid-x", False)
    assert res["success"] is True
    assert res["data"]["job_details"]["job_id"] == "jid-x"
    assert res["data"]["job_details"]["is_active"] is False


@pytest.mark.asyncio
async def test_delete_job_post_not_found(monkeypatch):
    svc = UpdateJobPost(db=None)

    async def fake_hard_delete(db, job_id):
        return False

    monkeypatch.setattr(
        "app.db.repository.job_post_repository.hard_delete_job_by_id",
        fake_hard_delete,
    )

    res = await svc.delete_job_post("jid-del")
    assert res["success"] is False
    assert res["status_code"] == 400


@pytest.mark.asyncio
async def test_delete_job_post_success(monkeypatch):
    svc = UpdateJobPost(db=None)

    async def fake_hard_delete(db, job_id):
        return True

    monkeypatch.setattr(
        "app.db.repository.job_post_repository.hard_delete_job_by_id",
        fake_hard_delete,
    )

    res = await svc.delete_job_post("jid-del")
    assert res["success"] is True
    assert res["data"]["job_id"] == "jid-del"
