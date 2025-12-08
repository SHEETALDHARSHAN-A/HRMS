import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db.repository import job_post_repository as jr
from datetime import datetime, timezone


class DummyRes:
    def __init__(self, rows=None):
        self._rows = rows or []
    def all(self):
        return self._rows
    def first(self):
        return self._rows[0] if self._rows else None
    def scalars(self):
        return self
    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None
    @property
    def rowcount(self):
        return 1 if self._rows else 0


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_success(monkeypatch):
    db = AsyncMock()
    # job titles, skills, locations each return a list of tuples
    db.execute.side_effect = [DummyRes([('SWE',)]), DummyRes([('Python',)]), DummyRes([('Pune',)])]
    res = await jr.get_search_autocomplete_suggestions(db)
    assert res['job_titles'] == ['SWE']
    assert res['skills'] == ['Python']
    assert res['locations'] == ['Pune']


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_exception(monkeypatch):
    db = AsyncMock()
    async def raise_exc(stmt, *args, **kwargs):
        raise Exception('db failure')
    db.execute.side_effect = raise_exc
    res = await jr.get_search_autocomplete_suggestions(db)
    assert res == {'job_titles': [], 'skills': [], 'locations': []}


@pytest.mark.asyncio
async def test_search_active_job_details_returns_rows(monkeypatch):
    db = AsyncMock()
    # Return one row with a mocked JobDetails and score
    jd = MagicMock()
    db.execute.return_value = DummyRes([(jd, 10)])
    res = await jr.search_active_job_details(db, 'Engineer', ['Python'], ['Pune'])
    assert isinstance(res, list)
    assert res[0][0] is jd
    assert res[0][1] == 10


@pytest.mark.asyncio
async def test_search_active_job_details_raises_on_db_error(monkeypatch):
    db = AsyncMock()
    async def raise_exc(stmt, *args, **kwargs):
        raise Exception('boom')
    db.execute.side_effect = raise_exc
    with pytest.raises(Exception):
        await jr.search_active_job_details(db, 'Eng', [], [])


def test_posted_date_desc_fallback(monkeypatch):
    # Temporarily replace JobDetails.posted_date with a simple value without desc()
    original = getattr(jr.JobDetails, 'posted_date', None)
    try:
        monkeypatch.setattr(jr.JobDetails, 'posted_date', 123)
        res = jr._posted_date_desc()
        assert res == 123
    finally:
        if original is not None:
            monkeypatch.setattr(jr.JobDetails, 'posted_date', original)


@pytest.mark.asyncio
async def test_get_job_details_by_id_invalid_uuid():
    db = AsyncMock()
    res = await jr.get_job_details_by_id(db, 'not-a-uuid')
    assert res is None


@pytest.mark.asyncio
async def test_job_exists_returns_false_for_none_db():
    assert await jr.job_exists(None, '1111') is False


@pytest.mark.asyncio
async def test_job_exists_with_invalid_uuid_returns_false():
    db = AsyncMock()
    assert await jr.job_exists(db, 'not-a-uuid') is False


@pytest.mark.asyncio
async def test_job_exists_found_true(monkeypatch):
    db = AsyncMock()
    db.execute.return_value = DummyRes([( 'id', )])
    assert await jr.job_exists(db, '11111111-1111-1111-1111-111111111111') is True


@pytest.mark.asyncio
async def test_get_all_job_details_returns_scalars(monkeypatch):
    db = AsyncMock()
    jd = MagicMock()
    db.execute.return_value = DummyRes([jd])
    res = await jr.get_all_job_details(db)
    assert res == [jd]


@pytest.mark.asyncio
async def test_get_active_job_details_returns_scalars(monkeypatch):
    db = AsyncMock()
    jd = MagicMock()
    db.execute.return_value = DummyRes([jd])
    res = await jr.get_active_job_details(db)
    assert res == [jd]


@pytest.mark.asyncio
async def test_get_jobs_by_user_id_returns_rows(monkeypatch):
    db = AsyncMock()
    jd = MagicMock()
    db.execute.return_value = DummyRes([jd])
    res = await jr.get_jobs_by_user_id(db, 'u1')
    assert res == [jd]


@pytest.mark.asyncio
async def test_get_agent_jobs_by_user_id_returns_rows(monkeypatch):
    db = AsyncMock()
    jd = MagicMock()
    db.execute.return_value = DummyRes([jd])
    # Ensure JobDetails has is_agent_interview attribute to allow building the query
    monkeypatch.setattr(jr.JobDetails, 'is_agent_interview', True, raising=False)
    res = await jr.get_agent_jobs_by_user_id(db, 'u1')
    assert res == [jd]


@pytest.mark.asyncio
async def test_update_or_create_job_details_create_missing_user_raises(monkeypatch):
    db = AsyncMock()
    job_data = {'job_title': 'SWE'}
    # user_id missing should raise
    with pytest.raises(ValueError):
        await jr.update_or_create_job_details(db, None, job_data)


@pytest.mark.asyncio
async def test_update_or_create_job_details_create_user_not_exist(monkeypatch):
    db = AsyncMock()
    # user existence check returns no rows
    def side_effect(stmt, *args, **kwargs):
        # emulates user check (text('SELECT 1 FROM users'))
        if 'SELECT 1 FROM users' in str(stmt):
            return DummyRes([])
        return DummyRes()
    db.execute.side_effect = side_effect
    job_data = {'job_title': 'SWE', 'user_id': 'u123'}
    with pytest.raises(ValueError):
        await jr.update_or_create_job_details(db, None, job_data)


@pytest.mark.asyncio
async def test_update_or_create_job_details_create_success(monkeypatch):
    db = AsyncMock()
    job_obj = MagicMock()
    # First call: user exists select -> return one row, second call: insert -> empty, final select -> return job
    def side_effect(stmt, *args, **kwargs):
        s = str(stmt)
        # user existence check
        if 'SELECT 1 FROM users' in s:
            return DummyRes([(1,)])
        # final select for job details
        if 'FROM job_details' in s or 'job_details' in s and 'SELECT' in s:
            return DummyRes([job_obj])
        # Default: return an empty DummyRes (for inserts/deletes)
        return DummyRes()
    db.execute.side_effect = side_effect
    job_data = {'job_title': 'SWE', 'user_id': 'u123', 'min_salary': '40,000', 'max_salary': '50000'}
    res = await jr.update_or_create_job_details(db, None, job_data, skills_data=[{'skill_name': 'Python'}], description_data=None, location_data=None, rounds_data=None, agent_configs_data=None)
    assert res == job_obj


@pytest.mark.asyncio
async def test_update_or_create_job_details_update_with_rounds_and_agent_config(monkeypatch):
    db = AsyncMock()
    job_obj = MagicMock()
    # Simulate select(JobDetails) returning job (for update path), update returns rowcount 1, deletes succeed, final select returns job
    def side_effect(stmt, *args, **kwargs):
        s = str(stmt)
        if 'SELECT job_details' in s or 'FROM job_details' in s or 'job_details' in s and 'SELECT' in s:
            return DummyRes([job_obj])
        # Any insert/delete returns DummyRes()
        return DummyRes()
    db.execute.side_effect = side_effect
    job_id = '11111111-1111-1111-1111-111111111111'
    rounds = [
        {'round_order': 1, 'round_name': 'Round 1', 'evaluation_criteria': {'shortlisting_criteria': 60, 'rejecting_criteria': 40}},
        {'round_order': 2, 'round_name': 'Round 2', 'evaluation_criteria': {'shortlisting_criteria': 50, 'rejecting_criteria': 50}},
    ]
    agent_configs = [
        {'roundListId': 1, 'persona': 'alex', 'role_fit': 80},
        {'roundName': 'Round 2', 'persona': 'alex', 'role_fit': 70},
    ]
    res = await jr.update_or_create_job_details(db, job_id, {'job_title': 'SWE'}, skills_data=None, description_data=None, location_data=None, rounds_data=rounds, agent_configs_data=agent_configs)
    assert res == job_obj
