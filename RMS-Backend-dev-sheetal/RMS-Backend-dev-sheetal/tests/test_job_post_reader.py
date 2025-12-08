import pytest

from app.services.job_post.job_post_reader import JobPostReader


@pytest.mark.asyncio
async def test_get_job_returns_none_when_repo_returns_none(monkeypatch):
    async def fake_get_job_details_by_id(db, job_id):
        return None

    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.get_job_details_by_id",
        fake_get_job_details_by_id,
    )

    reader = JobPostReader(db=None)
    res = await reader.get_job("nope")
    assert res is None


@pytest.mark.asyncio
async def test_get_job_returns_serialized(monkeypatch):
    async def fake_get_job_details_by_id(db, job_id):
        return {"raw": True, "id": job_id}

    def fake_serialize_job_details(raw):
        return {"serialized": True, "id": raw["id"]}

    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.get_job_details_by_id",
        fake_get_job_details_by_id,
    )
    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.serialize_job_details",
        fake_serialize_job_details,
    )

    reader = JobPostReader(db=None)
    out = await reader.get_job("job1")
    assert out == {"serialized": True, "id": "job1"}


@pytest.mark.asyncio
async def test_list_methods_map_serializers(monkeypatch):
    async def fake_get_all(db):
        return [{"id": "a"}, {"id": "b"}]

    async def fake_get_active(db):
        return [{"id": "a1"}]

    async def fake_get_by_user(db, user_id):
        return [{"id": f"u_{user_id}"}]

    def fake_serialize_details(raw):
        return {"d": raw["id"]}

    def fake_serialize_public(raw):
        return {"p": raw["id"]}

    def fake_serialize_admin(raw):
        return {"a": raw["id"]}

    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.get_all_job_details", fake_get_all
    )
    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.get_active_job_details", fake_get_active
    )
    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.get_jobs_by_user_id", fake_get_by_user
    )

    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.serialize_job_details", fake_serialize_details
    )
    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.serialize_public_job", fake_serialize_public
    )
    monkeypatch.setattr(
        "app.services.job_post.job_post_reader.serialize_admin_job", fake_serialize_admin
    )

    reader = JobPostReader(db=None)
    all_list = await reader.list_all()
    assert all_list == [{"d": "a"}, {"d": "b"}]

    active = await reader.list_active()
    assert active == [{"p": "a1"}]

    by_user = await reader.list_by_user("42")
    assert by_user == [{"a": "u_42"}]
