import pytest
from types import SimpleNamespace
from datetime import datetime

from app.db.repository import shortlist_repository as repo


@pytest.mark.asyncio
async def test_get_job_round_overview_filters_and_formats():
    # Rows: one with round_id None (should be ignored), another valid
    r_valid = SimpleNamespace(
        job_id='j1', job_title='Title1', round_id='r1', round_name='Round 1',
        round_order=1, total_candidates=2, shortlisted=1, under_review=0, rejected=1
    )
    r_none = SimpleNamespace(
        job_id='j2', job_title='Title2', round_id=None, round_name=None,
        round_order=None, total_candidates=0, shortlisted=0, under_review=0, rejected=0
    )

    class Res:
        def __init__(self, rows):
            self._rows = rows
        def fetchall(self):
            return self._rows

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res([r_valid, r_none])

    res = await repo.get_job_round_overview(FakeDB())
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]['job_id'] == 'j1'
    assert res[0]['round_name'] == 'Round 1'


@pytest.fixture(autouse=True)
def patch_sqlalchemy(monkeypatch):
    """Patch SQLAlchemy helpers used in shortlist_repository to prevent coercion errors in tests."""
    class SelectStub:
        def __init__(self, *a, **kw):
            pass
        def select_from(self, *a, **kw):
            return self
        def join(self, *a, **kw):
            return self
        def where(self, *a, **kw):
            return self
        def group_by(self, *a, **kw):
            return self
        def order_by(self, *a, **kw):
            return self
    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)
    monkeypatch.setattr(repo, 'and_', lambda *a, **kw: a, raising=False)
    class UpdateStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def values(self, *a, **kw):
            return self
        def execution_options(self, *a, **kw):
            return self
    monkeypatch.setattr(repo, 'update', UpdateStub, raising=False)


@pytest.mark.asyncio
async def test_update_interview_round_status_commits_and_returns():
    class Res:
        def __init__(self, rc=1):
            self.rowcount = rc

    class FakeDB:
        def __init__(self, rc=1):
            self._rc = rc
            self.committed = False
        async def execute(self, stmt, *a, **kw):
            return Res(rc=self._rc)
        async def commit(self):
            self.committed = True

    fb = FakeDB(rc=1)
    assert await repo.update_interview_round_status(fb, 'p1', 'r1', 'shortlisted') is True
    fb2 = FakeDB(rc=0)
    assert await repo.update_interview_round_status(fb2, 'p1', 'r1', 'shortlisted') is False


@pytest.mark.asyncio
async def test_get_round_candidates_formats_and_experience():
    resume = {'experience': [{'years': 2}]}
    row = SimpleNamespace(
        profile_id='p1', candidate_name='Name', candidate_email='a@b', resume_data=resume,
        result='shortlist', overall_score=85, score_explanation='ok', reason='good',
        potential_score=10, location_score=5, role_fit_score=7, skill_score=9, skill_score_explanation={},
        round_status='shortlisted', round_name='Round 1'
    )

    class Res:
        def __init__(self, rows):
            self._rows = rows
        def fetchall(self):
            return self._rows

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res([row])

    out = await repo.get_round_candidates(FakeDB(), 'job1', 'r1', None)
    assert isinstance(out, list) and out[0]['profile_id'] == 'p1'
    assert 'Years' in out[0]['experience_level']


@pytest.mark.asyncio
async def test_upsert_shortlist_result_errors_and_update():
    # invalid result
    class FakeDB: pass
    with pytest.raises(ValueError):
        await repo.upsert_shortlist_result(FakeDB(), 'p1', 'invalid', 'reason')

    # entry not found
    class ResNotFound:
        def scalar_one_or_none(self):
            return None
    class FakeDB2:
        async def execute(self, stmt, *a, **kw):
            return ResNotFound()

    with pytest.raises(ValueError):
        await repo.upsert_shortlist_result(FakeDB2(), 'p1', 'shortlist', 'reason')

    # entry found and updated
    entry = SimpleNamespace(profile_id='p1', result='under_review', reason=None, updated_at=None)
    class ResFound:
        def scalar_one_or_none(self):
            return entry
    class FakeDB3:
        def __init__(self):
            self.committed = False
            self.refreshed = False
        async def execute(self, stmt, *a, **kw):
            return ResFound()
        async def commit(self):
            self.committed = True
        async def refresh(self, o):
            self.refreshed = True

    r = await repo.upsert_shortlist_result(FakeDB3(), 'p1', 'shortlist', 'good')
    assert r.result == 'shortlist'
    assert r.reason == 'good'
