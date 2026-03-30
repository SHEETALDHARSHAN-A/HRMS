import pytest
from types import SimpleNamespace
from uuid import UUID, uuid4
from datetime import datetime

from app.db.repository import scheduling_repository as repo


# SQLAlchemy stubs for repository unit tests
class SelectStub:
    def __init__(self, *a, **kw):
        pass

    def where(self, *a, **kw):
        return self

    def order_by(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def select_from(self, *a, **kw):
        return self

    def join(self, *a, **kw):
        return self

    def label(self, *a, **kw):
        return self

    def asc(self):
        return self


class UpdateStub:
    def __init__(self, *a, **kw):
        pass

    def where(self, *a, **kw):
        return self

    def values(self, *a, **kw):
        return self


class InsertStub:
    def __init__(self, *a, **kw):
        pass

    def values(self, *a, **kw):
        return self


@pytest.fixture(autouse=True)
def patch_sqlalchemy(monkeypatch):
    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)
    monkeypatch.setattr(repo, 'update', UpdateStub, raising=False)
    monkeypatch.setattr(repo, 'insert', InsertStub, raising=False)


@pytest.mark.asyncio
async def test_get_candidate_details_for_scheduling_basic():
    # Fake rows returned as tuples: (UUID, name, email, phone)
    uid = uuid4()

    class Res:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res([(uid, 'First Last', 'f@l.com', '123')])

    res = await repo.get_candidate_details_for_scheduling(FakeDB(), [str(uid)])
    assert isinstance(res, list)
    assert res[0]['profile_id'] == str(uid)
    assert res[0]['first_name'] == 'First'
    assert res[0]['last_name'] == 'Last'


@pytest.mark.asyncio
async def test_check_existing_schedules_returns_strings():
    class Res:
        def scalars(self):
            return self

        def all(self):
            return [UUID(int=1), UUID(int=2)]

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res()

    res = await repo.check_existing_schedules(FakeDB(), 'job1', ['a', 'b'])
    assert isinstance(res, list)
    assert all(isinstance(x, str) for x in res)


@pytest.mark.asyncio
async def test_check_existing_schedules_round_aware_match():
    req_round = uuid4()
    p1 = uuid4()
    p2 = uuid4()
    p3 = uuid4()

    rows = [
        SimpleNamespace(profile_id=p1, scheduled_round_id=req_round, interview_round_id=None, round_list_id=None),
        SimpleNamespace(profile_id=p2, scheduled_round_id=uuid4(), interview_round_id=uuid4(), round_list_id=req_round),
        SimpleNamespace(profile_id=p3, scheduled_round_id=uuid4(), interview_round_id=uuid4(), round_list_id=uuid4()),
    ]

    class Res:
        def fetchall(self):
            return rows

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res()

    out = await repo.check_existing_schedules(
        FakeDB(),
        'job1',
        [str(p1), str(p2), str(p3)],
        requested_round_id=str(req_round),
    )
    assert set(out) == {str(p1), str(p2)}


@pytest.mark.asyncio
async def test_create_schedules_batch_success_and_fallback(monkeypatch):
    # Case 1: Scheduling accepts kwargs (simulate SQLAlchemy model)
    called = {'added': 0, 'committed': False}

    class DummySchedule:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    monkeypatch.setattr(repo, 'Scheduling', DummySchedule)

    class FakeDB:
        def __init__(self):
            self.added = []

        def add_all(self, arr):
            self.added.extend(arr)

        async def commit(self):
            called['committed'] = True

    data = [{'profile_id': 'p1'}, {'profile_id': 'p2'}]
    res = await repo.create_schedules_batch(FakeDB(), data)
    assert res == ['p1', 'p2']

    # Case 2: Scheduling raises TypeError -> fallback to SimpleNamespace
    class SchedulingFail:
        def __init__(self, **kwargs):
            raise TypeError("no kwargs")

    monkeypatch.setattr(repo, 'Scheduling', SchedulingFail)

    class FakeDB2:
        def __init__(self):
            self.added = []

        def add_all(self, arr):
            self.added.extend(arr)

        async def commit(self):
            called['committed'] = True

    res2 = await repo.create_schedules_batch(FakeDB2(), [{'profile_id': 'p3'}])
    assert res2 == ['p3']


@pytest.mark.asyncio
async def test_update_schedule_email_status_and_get_job_title(monkeypatch):
    class ResRow:
        def __init__(self, rc=1, val=None):
            self.rowcount = rc
            self._val = val

        def scalar_one_or_none(self):
            return self._val

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            # For update call -> return rowcount > 0
            return ResRow(rc=1)

        async def commit(self):
            return None

    assert await repo.update_schedule_email_status(FakeDB(), 'p1', 'job1', True) is True

    # get_job_title_by_id
    class FakeDB2:
        async def execute(self, stmt, *a, **kw):
            return ResRow(val='Engineer')

    assert await repo.get_job_title_by_id(FakeDB2(), 'job1') == 'Engineer'


@pytest.mark.asyncio
async def test_get_round_name_and_next_round_details(monkeypatch):
    # get_round_name_by_id invalid uuid -> None
    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return SimpleNamespace(scalar_one_or_none=lambda: 'Round 1')

    assert (await repo.get_round_name_by_id(FakeDB(), 'not-a-uuid')) is None

    # valid uuid returns dict
    uid = str(uuid4())
    class FakeDB2:
        async def execute(self, stmt, *a, **kw):
            return SimpleNamespace(scalar_one_or_none=lambda: 'Screen')

    got = await repo.get_round_name_by_id(FakeDB2(), uid)
    assert got == {'round_name': 'Screen'}

    # get_next_round_details: not found current -> None
    class FakeDB3:
        async def execute(self, stmt, *a, **kw):
            # called first for current_round_stmt -> return None
            return SimpleNamespace(scalar_one_or_none=lambda: None)

    assert await repo.get_next_round_details(FakeDB3(), str(uuid4()), str(uuid4())) is None

    # get_next_round_details: found next
    class FakeDB4:
        def __init__(self):
            self._calls = 0

        async def execute(self, stmt, *a, **kw):
            self._calls += 1
            if self._calls == 1:
                return SimpleNamespace(scalar_one_or_none=lambda: 1)
            return SimpleNamespace(scalar_one_or_none=lambda: 'Technical')

    uid1 = str(uuid4())
    uid2 = str(uuid4())
    res = await repo.get_next_round_details(FakeDB4(), uid1, uid2)
    assert res == {'round_name': 'Technical'}


@pytest.mark.asyncio
async def test_resolve_round_instance_id_for_schedule_invalid_uuid_fallback():
    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            raise AssertionError("execute should not be called for invalid UUID inputs")

    out = await repo.resolve_round_instance_id_for_schedule(
        FakeDB(),
        job_id='bad-job-id',
        profile_id='bad-profile-id',
        requested_round_id='not-a-uuid',
    )
    assert out == 'not-a-uuid'


@pytest.mark.asyncio
async def test_get_scheduled_interviews_returns_formatted_list():
    # mimic rows returned by select...join
    uuid_job = uuid4()
    uuid_profile = uuid4()
    uuid_round = uuid4()

    class Row:
        def __init__(self):
            self.profile_id = uuid_profile
            self.job_id = uuid_job
            self.round_id = uuid_round
            self.scheduled_datetime = datetime.utcnow()
            self.status = 'PENDING'
            self.interview_token = uuid4()
            self.interview_type = 'VIDEO'
            self.level_of_interview = 'L1'
            self.candidate_name = 'John Doe'
            self.candidate_email = 'john@example.com'
            self.job_title = 'Engineer'
            self.round_name = 'Screen'

    class Res:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class FakeDB:
        async def execute(self, stmt, *a, **kw):
            return Res([Row()])

    res = await repo.get_scheduled_interviews(str(uuid_job), str(uuid_round), FakeDB())
    assert len(res) == 1
    assert res[0]['candidate_name'] == 'John Doe'
    assert res[0]['job_title'] == 'Engineer'

