import pytest
from types import SimpleNamespace

from app.db.repository import profile_repository as repo


class SelectStub:
    def __init__(self, *a, **kw):
        pass

    def select_from(self, *a, **kw):
        return self

    def where(self, *a, **kw):
        return self


@pytest.fixture(autouse=True)
def patch_select(monkeypatch):
    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)


@pytest.mark.asyncio
async def test_count_by_status_applied_and_none():
    class Res:
        def __init__(self, val):
            self._val = val

        def scalar(self):
            return self._val

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res(2)

    repo_obj = repo.ProfileRepository(FakeDB())

    assert await repo_obj.count_by_status('job1', None) == 2
    assert await repo_obj.count_by_status('job1', 'applied') == 2


@pytest.mark.asyncio
async def test_count_by_status_other_status_uses_interview_rounds():
    class Res:
        def __init__(self, val):
            self._val = val

        def scalar(self):
            return self._val

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res(5)

    repo_obj = repo.ProfileRepository(FakeDB())
    assert await repo_obj.count_by_status('job1', 'PASSED') == 5
