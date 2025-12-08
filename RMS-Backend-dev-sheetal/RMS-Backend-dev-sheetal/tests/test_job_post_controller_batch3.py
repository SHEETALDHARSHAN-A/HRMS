import pytest
from types import SimpleNamespace
import app.controllers.job_post_controller as jpc


async def fake_get_db():
    yield "FAKE_DB"


class DummyRequest:
    def __init__(self, user=None):
        self.state = SimpleNamespace(user=user)


@pytest.mark.asyncio
async def test_get_all_jobs_controller(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def list_all(self):
            return [{"job_id": "j1"}, {"job_id": "j2"}]

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)
    # Filter should just return same list
    monkeypatch.setattr(jpc.JobPostPermissions, 'filter_jobs_by_ownership', lambda jobs, user: jobs)

    res = await jpc.get_all_jobs_controller(request=None)
    assert res.get('success') is True
    assert isinstance(res.get('data', {}).get('jobs'), list)


@pytest.mark.asyncio
async def test_get_my_jobs_controller_unauthenticated():
    res = await jpc.get_my_jobs_controller(request=DummyRequest(user=None))
    assert res.get('success') is False
    assert res.get('status_code') == 401


@pytest.mark.asyncio
async def test_get_my_jobs_controller_happy(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def list_all(self):
            return []

        async def list_by_user(self, user_id):
            return [{"job_id": "u1", "created_by_user_id": user_id}]

    monkeypatch.setattr(jpc, 'JobPostReader', FakeReader)
    monkeypatch.setattr(jpc.JobPostPermissions, 'filter_jobs_by_ownership', lambda jobs, user, show_own_only=False: jobs)

    req = DummyRequest(user={"user_id": "user-1"})
    res = await jpc.get_my_jobs_controller(request=req)
    assert res.get('success') is True
    assert isinstance(res.get('data', {}).get('jobs'), list)


@pytest.mark.asyncio
async def test_search_public_jobs_controller_bad_request():
    # Provide fake search service but no query params -> should 400
    fake_service = SimpleNamespace(search_jobs=lambda search_role, search_skills, search_locations: [])
    res = await jpc.search_public_jobs_controller(search_service=fake_service, role=None, skills=None, locations=None)
    assert res.get('success') is False
    assert res.get('status_code') == 400


@pytest.mark.asyncio
async def test_search_public_jobs_controller_happy(monkeypatch):
    async def _search_jobs(search_role, search_skills, search_locations):
        return [{"job_id": "j1"}]

    fake_service = SimpleNamespace(search_jobs=_search_jobs)
    res = await jpc.search_public_jobs_controller(search_service=fake_service, role='Dev', skills='py', locations=None)
    assert res.get('success') is True
    assert isinstance(res.get('data', {}).get('jobs'), list)


@pytest.mark.asyncio
async def test_get_search_suggestions_controller(monkeypatch):
    async def _get_suggestions():
        return ["a", "b"]

    fake_service = SimpleNamespace(get_suggestions=_get_suggestions)
    res = await jpc.get_search_suggestions_controller(search_service=fake_service)
    assert res.get('success') is True
    assert isinstance(res.get('data'), list) or isinstance(res.get('data'), dict)


@pytest.mark.asyncio
async def test_candidate_stats_controller_invalid_uuid():
    res = await jpc.candidate_stats_controller('not-uuid')
    assert res.get('success') is False
    assert res.get('status_code') == 400


@pytest.mark.asyncio
async def test_candidate_stats_controller_happy(monkeypatch):
    monkeypatch.setattr(jpc, 'get_db', fake_get_db)

    class FakeRepo:
        def __init__(self, db):
            pass

        async def count_by_status(self, job_id, status=None):
            return 1

    # patch the ProfileRepository where it's defined
    monkeypatch.setattr('app.db.repository.profile_repository.ProfileRepository', lambda db: FakeRepo(db))

    res = await jpc.candidate_stats_controller('11111111-1111-1111-1111-111111111111')
    assert res.get('success') is True
    assert isinstance(res.get('data', {}).get('profile_counts'), dict)
