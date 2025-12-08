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
    # Provide safe stubs for SQLAlchemy functions used in job_post_repository
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
        def distinct(self, *a, **kw):
            return self
        def limit(self, *a, **kw):
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
            self._values = kw if kw else None
            return self
        def __str__(self):
            return "INSERT"

    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)
    monkeypatch.setattr(repo, 'update', UpdateStub, raising=False)
    monkeypatch.setattr(repo, 'delete', DeleteStub, raising=False)
    monkeypatch.setattr(repo, 'insert', InsertStub, raising=False)
    monkeypatch.setattr(repo, 'aliased', lambda x: x, raising=False)


@pytest.mark.asyncio
async def test_create_job_with_rounds_and_agent_configs(monkeypatch):
    # Set up a FakeDB that records executed statements for inspection
    class FakeDB:
        def __init__(self):
            self.executed = []
            self.call_count = 0
        async def execute(self, q, *args, **kwargs):
            self.call_count += 1
            self.executed.append(q)
            # Return defaults for select()/insert() expectations
            # First call: user_exists select -> return first (exists)
            if self.call_count == 1:
                return Res(first=(1,))
            # subsequent inserts return rowcount
            return Res(rowcount=1)
        async def commit(self):
            return None
        async def rollback(self):
            return None

    db = FakeDB()

    # Provide minimal table definitions used in the repo
    monkeypatch.setattr(repo, 'JobDetails', SimpleNamespace(__table__=SimpleNamespace(columns=[SimpleNamespace(name='user_id'), SimpleNamespace(name='id')]), id=SimpleNamespace(name='id')), raising=False)
    monkeypatch.setattr(repo, 'RoundList', SimpleNamespace(id=SimpleNamespace(name='id'), job_id=SimpleNamespace(name='job_id')), raising=False)
    monkeypatch.setattr(repo, 'EvaluationCriteria', SimpleNamespace(id=SimpleNamespace(name='id'), job_id=SimpleNamespace(name='job_id'), round_id=SimpleNamespace(name='round_id')), raising=False)
    monkeypatch.setattr(repo, 'AgentRoundConfig', SimpleNamespace(id=SimpleNamespace(name='id'), job_id=SimpleNamespace(name='job_id'), round_list_id=SimpleNamespace(name='round_list_id')), raising=False)
    monkeypatch.setattr(repo, 'JobSkills', SimpleNamespace(id=SimpleNamespace(name='id')), raising=False)
    monkeypatch.setattr(repo, 'JobDescription', SimpleNamespace(id=SimpleNamespace(name='id'), job_id=SimpleNamespace(name='job_id')), raising=False)
    monkeypatch.setattr(repo, 'LocationList', SimpleNamespace(id=SimpleNamespace(name='id'), location=SimpleNamespace(name='location')), raising=False)
    monkeypatch.setattr(repo, 'JobLocations', SimpleNamespace(id=SimpleNamespace(name='id'), job_id=SimpleNamespace(name='job_id'), location_id=SimpleNamespace(name='location_id')), raising=False)

    # Inputs: rounds and agent_configs
    rounds_data = [
        {"round_order": 1, "round_name": "Screen", "evaluation_criteria": {"shortlisting_criteria": 60, "rejecting_criteria": 40}}
    ]
    agent_configs_data = [
        {"roundListId": 1, "interview_mode": "agent", "persona": "alex", "role_fit": 80}
    ]

    # Run creating job path
    job_data = {"user_id": "u1", "job_title": "Test Job"}
    created_job = await repo.update_or_create_job_details(db, None, job_data, skills_data=None, description_data=None, location_data=None, rounds_data=rounds_data, agent_configs_data=agent_configs_data)

    # Expect the final fetch to return None in our fake DB (Res scalar defaults to None), we just ensure inserts called
    assert db.call_count >= 3
    # Check that inserts or deletes were invoked for rounds and agent configs by matching 'INSERT'/'DELETE' strings on statements or stub types
    assert any(str(q).startswith('INSERT') or 'insert' in str(q).lower() for q in db.executed)
import pytest
from unittest.mock import AsyncMock

from app.db.repository import job_post_repository as repo


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_success(fake_db):
    # Prepare fake results for job titles, skills and locations in sequence
    class Result:
        def __init__(self, rows):
            self._rows = rows
        def all(self):
            return self._rows

    r1 = Result([("Engineer",)])
    r2 = Result([("Python",)])
    r3 = Result([("Remote",)])

    fake_db.execute = AsyncMock()
    fake_db.execute.side_effect = [r1, r2, r3]

    # Patch select to a harmless stub so SQLAlchemy coercion is avoided
    class _SelectStub:
        def where(self, *a, **k):
            return self
        def distinct(self, *a, **k):
            return self
        def options(self, *a, **k):
            return self

    repo.select = lambda *a, **k: _SelectStub()

    res = await repo.get_search_autocomplete_suggestions(fake_db)
    assert res["job_titles"] == ["Engineer"]
    assert res["skills"] == ["Python"]
    assert res["locations"] == ["Remote"]


def test__job_details_load_options_returns_list():
    # Should return a list (may be empty in test environments)
    opts = repo._job_details_load_options()
    assert isinstance(opts, list)
