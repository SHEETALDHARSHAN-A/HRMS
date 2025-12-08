import uuid
import pytest
from types import SimpleNamespace
from app.db.repository import job_post_repository as repo


class Res:
    def __init__(self, rows=None, first=None, scalar=None, rowcount=0):
        self._rows = rows or []
        self._first = first
        self._scalar = scalar
        self.rowcount = rowcount

    def scalars(self):
        return self

    def first(self):
        return self._first

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._scalar

    def fetchall(self):
        return self._rows


@pytest.fixture(autouse=True)
def patch_sqlalchemy(monkeypatch):
    class SelectStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def options(self, *a, **kw):
            return self
        def select_from(self, *a, **kw):
            return self
        def outerjoin(self, *a, **kw):
            return self
        def group_by(self, *a, **kw):
            return self
        def having(self, *a, **kw):
            return self
        def order_by(self, *a, **kw):
            return self
        def limit(self, *a, **kw):
            return self
        def distinct(self, *a, **kw):
            return self
        def label(self, *a, **kw):
            return self
        def __str__(self):
            return "SELECT"

    class UpdateStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def values(self, *a, **kw):
            return self
        def execution_options(self, *a, **kw):
            return self
        def __str__(self):
            return "UPDATE"

    class DeleteStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def __str__(self):
            return "DELETE"

    class InsertStub:
        def __init__(self, *a, **kw):
            pass
        def values(self, *a, **kw):
            return self
        def __str__(self):
            return "INSERT"

    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)
    monkeypatch.setattr(repo, 'update', UpdateStub, raising=False)
    monkeypatch.setattr(repo, 'delete', DeleteStub, raising=False)
    monkeypatch.setattr(repo, 'insert', InsertStub, raising=False)
    def aliased_stub(x):
        attrs = {}
        for a in ('id', 'skill_name', 'location', 'location_id', 'job_id', 'skill_id', 'first_name', 'last_name', 'user_id'):
            if hasattr(x, a):
                attrs[a] = getattr(x, a)
        return SimpleNamespace(**attrs)
    monkeypatch.setattr(repo, 'aliased', aliased_stub, raising=False)

    class ColShim:
        def __init__(self, name):
            self.name = name
        def ilike(self, x):
            return PseudoExpr(f"{self.name} ilike {x}")
        def in_(self, x):
            return PseudoExpr(f"{self.name} in {x}")
        def is_not(self, x):
            return PseudoExpr(f"{self.name} is_not {x}")
        def desc(self):
            return self
        def __str__(self):
            return self.name

    class TableShim:
        def __init__(self, names):
            self.columns = [SimpleNamespace(name=n) for n in names]

    class PseudoExpr:
        def __init__(self, val):
            self.val = val
        def __and__(self, other):
            return self
        def __rand__(self, other):
            return self
        def __str__(self):
            return self.val
        def __bool__(self):
            # Prevent boolean evaluation
            return True

    # Minimal shims for models used in these tests
    monkeypatch.setattr(repo, 'JobDetails', SimpleNamespace(
        id=ColShim('id'), job_title=ColShim('job_title'), posted_date=ColShim('posted_date'), user_id=ColShim('user_id'), is_active=ColShim('is_active'), work_mode=ColShim('work_mode'), __table__=TableShim(['id', 'job_title', 'user_id', 'minimum_salary', 'maximum_salary', 'rounds_count'])
    ), raising=False)
    monkeypatch.setattr(repo, 'SkillList', SimpleNamespace(skill_name=ColShim('skill_name')), raising=False)
    repo.SkillList.id = ColShim('id')
    monkeypatch.setattr(repo, 'LocationList', SimpleNamespace(location=ColShim('location')), raising=False)
    repo.LocationList.id = ColShim('id')
    # Also make available placeholders of other models used in job queries
    monkeypatch.setattr(repo, 'JobSkills', SimpleNamespace(id=ColShim('id'), job_id=ColShim('job_id'), skill_id=ColShim('skill_id')), raising=False)
    monkeypatch.setattr(repo, 'JobDescription', SimpleNamespace(job_id=ColShim('job_id'), id=ColShim('id')), raising=False)
    monkeypatch.setattr(repo, 'JobLocations', SimpleNamespace(job_id=ColShim('job_id'), location=ColShim('location'), id=ColShim('id'), location_id=ColShim('location_id')), raising=False)
    monkeypatch.setattr(repo, 'RoundList', SimpleNamespace(id=ColShim('id'), job_id=ColShim('job_id')), raising=False)
    monkeypatch.setattr(repo, 'EvaluationCriteria', SimpleNamespace(job_id=ColShim('job_id'), round_id=ColShim('round_id')), raising=False)


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_returns_lists():
    class FakeDB:
        def __init__(self):
            self.i = 0
        async def execute(self, q, *a, **kw):
            self.i += 1
            # first call -> job_title, second -> skill, third -> loc
            if self.i == 1:
                return Res(rows=[('Senior Developer',), ('Junior',)])
            if self.i == 2:
                return Res(rows=[('python',), ('sql',)])
            if self.i == 3:
                return Res(rows=[('Bengaluru',), ('Remote',)])
            return Res(rows=[])

    res = await repo.get_search_autocomplete_suggestions(FakeDB())
    assert 'job_titles' in res
    assert res['job_titles'] == ['Senior Developer', 'Junior']
    assert 'skills' in res and res['skills'] == ['python', 'sql']
    assert 'locations' in res and res['locations'] == ['Bengaluru', 'Remote']


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_handles_exception():
    class FakeDB:
        async def execute(self, q, *a, **kw):
            raise Exception('db error')

    res = await repo.get_search_autocomplete_suggestions(FakeDB())
    assert res == {"job_titles": [], "skills": [], "locations": []}


@pytest.mark.asyncio
async def test_search_active_job_details_returns_results():
    # Return two results: a SimpleNamespace job and a score
    class FakeDB:
        def async_execute(self, q, *a, **kw):
            return Res(rows=[(SimpleNamespace(id='jid1', job_title='J1'), 10), (SimpleNamespace(id='jid2', job_title='J2'), 5)])
        async def execute(self, q, *a, **kw):
            return Res(rows=[(SimpleNamespace(id='jid1', job_title='J1'), 10), (SimpleNamespace(id='jid2', job_title='J2'), 5)])

    results = await repo.search_active_job_details(FakeDB(), 'Dev', ['python'], ['Bengaluru'])
    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0][1] == 10


@pytest.mark.asyncio
async def test_job_exists_and_get_job_details_by_id():
    class FakeDB:
        async def execute(self, q, *a, **kw):
            # For job_exists: select(JobDetails.id)... return scalar
            return Res(scalar=1)

    job_id = str(uuid.uuid4())
    assert await repo.job_exists(FakeDB(), job_id) is True
    # invalid uuid -> False
    assert await repo.job_exists(FakeDB(), 'not-a-uuid') is False


@pytest.mark.asyncio
async def test_update_or_create_job_details_create_and_return():
    # Test the create path (job_id None)
    created_uuid = str(uuid.uuid4())
    class FakeDB:
        def __init__(self):
            self.calls = 0
        async def execute(self, q, *a, **kw):
            self.calls += 1
            # 1: user_exists
            if self.calls == 1:
                return Res(first=(1,))
            # 2: insert JobDetails
            if self.calls == 2:
                return Res(rowcount=1)
            # final select -> return created job
            return Res(scalar=SimpleNamespace(id=created_uuid, job_title='J1'))
        async def commit(self):
            return None
        async def rollback(self):
            return None

    job_data = {
        'user_id': 'u1',
        'min_salary': '1000',
        'max_salary': '2000',
        'job_title': 'Test Job'
    }
    res_job = await repo.update_or_create_job_details(FakeDB(), None, job_data, skills_data=None, description_data=None, location_data=None, rounds_data=None, agent_configs_data=None)
    assert res_job is not None
    assert res_job.job_title == 'J1'
import pytest
from unittest.mock import AsyncMock

from app.db.repository.job_post_repository import (
    get_search_autocomplete_suggestions,
    get_job_details_by_id,
    search_active_job_details,
)
import app.db.repository.job_post_repository as repo


# Provide minimal column-like shims so repository query construction
# doesn't attempt to call SQLAlchemy on test-side SimpleNamespaces.
class _ColShim:
    def __init__(self, name):
        self.name = name

    def is_not(self, other):
        return self

    def __ne__(self, other):
        return self


@pytest.fixture(autouse=True)
def patch_job_models(monkeypatch):
    monkeypatch.setattr(repo, 'JobDetails', __import__('types').SimpleNamespace(job_title=_ColShim('job_title'), is_active=_ColShim('is_active')), raising=False)
    monkeypatch.setattr(repo, 'SkillList', __import__('types').SimpleNamespace(skill_name=_ColShim('skill_name')), raising=False)
    monkeypatch.setattr(repo, 'LocationList', __import__('types').SimpleNamespace(location=_ColShim('location')), raising=False)
    yield


class MockResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        # return first row element for scalar
        if not self._rows:
            return None
        r = self._rows[0]
        # if tuple, return first; else return as-is
        return r[0] if isinstance(r, tuple) else r


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_success():
    mock_db = AsyncMock()

    # job titles, skills, locations -> each execute call returns a MockResult
    job_titles = [("Dev",), ("Engineer",)]
    skills = [("Python",), ("SQL",)]
    locations = [("Remote",), ("NY",)]

    mock_db.execute.side_effect = [
        MockResult(job_titles),
        MockResult(skills),
        MockResult(locations),
    ]

    # Ensure module-level column shims are present (tests may modify them)
    repo.JobDetails.job_title = _ColShim('job_title')
    repo.SkillList.skill_name = _ColShim('skill_name')
    repo.LocationList.location = _ColShim('location')

    out = await get_search_autocomplete_suggestions(mock_db)

    assert out["job_titles"] == ["Dev", "Engineer"]
    assert out["skills"] == ["Python", "SQL"]
    assert out["locations"] == ["Remote", "NY"]


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_db_failure():
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("boom")

    out = await get_search_autocomplete_suggestions(mock_db)

    assert out == {"job_titles": [], "skills": [], "locations": []}


def test_get_job_details_by_id_invalid_uuid():
    # no db needed; invalid uuid should return None
    import asyncio

    async def run():
        return await get_job_details_by_id(None, "not-a-uuid")

    res = asyncio.get_event_loop().run_until_complete(run())
    assert res is None


@pytest.mark.asyncio
async def test_search_active_job_details_db_error_raises():
    mock_db = AsyncMock()
    # Make db.execute raise inside function
    mock_db.execute.side_effect = Exception("db fail")

    with pytest.raises(Exception):
        await search_active_job_details(mock_db, search_role="dev", search_skills=["py"], search_locations=["remote"])
