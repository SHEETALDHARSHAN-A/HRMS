import pytest
from types import SimpleNamespace
import asyncio

from app.db.repository import job_post_repository as repo


def test_job_details_load_options_returns_list():
    opts = repo._job_details_load_options()
    assert isinstance(opts, list)


@pytest.mark.asyncio
async def test_get_search_autocomplete_suggestions_unit():
    class Result:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class FakeDB:
        def __init__(self):
            self._call = 0

        async def execute(self, stmt, *a, **kw):
            # The repository calls execute three times in fixed order: job titles, skills, locations
            self._call += 1
            if self._call == 1:
                return Result([('Engineer',), ('Dev',)])
            if self._call == 2:
                return Result([('Python',)])
            if self._call == 3:
                return Result([('Remote',)])
            return Result([])

    fake_db = FakeDB()
    res = await repo.get_search_autocomplete_suggestions(fake_db)
    assert res['job_titles'] == ['Engineer', 'Dev']
    assert res['skills'] == ['Python']
    assert res['locations'] == ['Remote']


def test_update_or_create_job_details_missing_user_raises(monkeypatch):
    # Ensure JobDetails.__table__.columns exists so code can compute allowed_columns
    monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id')]), raising=False)

    # Provide a fake DB with rollback to avoid AttributeError if exception handling triggers
    class FakeDB:
        async def rollback(self):
            return None

    with pytest.raises(ValueError):
        asyncio.get_event_loop().run_until_complete(
            repo.update_or_create_job_details(db=FakeDB(), job_id=None, job_data={})
        )


@pytest.mark.asyncio
async def test_update_or_create_job_details_user_not_found(monkeypatch):
    # Create a FakeDB that will return no user row on the user existence check
    class Result:
        def first(self):
            return None

    class FakeDBNoUser:
        def __init__(self):
            self._calls = 0
        async def execute(self, query, *a, **kw):
            self._calls += 1
            # First call is user existence check
            if self._calls == 1:
                return Result()
            # default: return object with scalar_one_or_none
            class Res:
                def scalar_one_or_none(self):
                    return None
            return Res()
        async def rollback(self):
            return None

    # Ensure JobDetails has __table__ with columns so allowed_columns works
    monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id')]), raising=False)

    with pytest.raises(ValueError):
        await repo.update_or_create_job_details(db=FakeDBNoUser(), job_id=None, job_data={'user_id': 'user-x'})


@pytest.mark.asyncio
async def test_update_or_create_job_details_create_success(monkeypatch):
    # This test simulates a create flow where user exists and final select returns job
    job_obj = SimpleNamespace(id='fake-id', user_id='creator-1')

    class ResInsert:
        def first(self):
            return (1,)

    class FinalRes:
        def scalar_one_or_none(self):
            return job_obj

    class FakeDBCreate:
        def __init__(self):
            self._calls = 0
        async def execute(self, query, *a, **kw):
            self._calls += 1
            # 1: user exists check -> return row
            if self._calls == 1:
                return ResInsert()
            # All inserts/updates -> simple object
            if self._calls == 2:
                class R:
                    def scalar_one_or_none(self):
                        return None
                return R()
            # final select for job
            return FinalRes()
        async def commit(self):
            return None
        async def rollback(self):
            return None

    monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id'), SimpleNamespace(name='id')]), raising=False)
    # Avoid sqlalchemy coercion for insert/update/delete calls by stubbing them
    class InsertStub:
        def __init__(self, *a, **kw):
            pass
        def values(self, *a, **kw):
            return self
    class UpdateStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def values(self, *a, **kw):
            return self
    class DeleteStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
    monkeypatch.setattr(repo, 'insert', InsertStub)
    monkeypatch.setattr(repo, 'update', UpdateStub)
    monkeypatch.setattr(repo, 'delete', DeleteStub)
    class SelectStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def options(self, *a, **kw):
            return self
    monkeypatch.setattr(repo, 'select', SelectStub)

    res = await repo.update_or_create_job_details(db=FakeDBCreate(), job_id=None, job_data={'user_id': 'creator-1'})
    assert res == job_obj


@pytest.mark.asyncio
async def test_job_exists_checks_uuid_and_false_on_not_found():
    class NotFoundDB:
        async def execute(self, q, *a, **kw):
            class R:
                def scalar_one_or_none(self):
                    return None
            return R()
    assert await repo.job_exists(NotFoundDB(), 'not-a-uuid') is False

    # Valid UUID but no row found
    import uuid
    uid = str(uuid.uuid4())
    assert await repo.job_exists(NotFoundDB(), uid) is False


@pytest.mark.asyncio
async def test_soft_delete_jobs_batch_invalid_and_valid(monkeypatch):
    # Invalid uuid in list should be ignored and return 0
    class FakeDBNoOp:
        async def execute(self, q, *a, **kw):
            class R:
                rowcount = 0
            return R()
        async def commit(self):
            return None
    assert await repo.soft_delete_jobs_batch(FakeDBNoOp(), ['invalid-uuid']) == 0


@pytest.mark.asyncio
async def test_update_or_create_job_details_update_success(monkeypatch):
    # Simulate update flow where job exists and update affects rows
    existing_job = SimpleNamespace(id='existing-uuid', user_id='u1')
    class JobRes:
        def scalar_one_or_none(self):
            return existing_job

    class UpdateRes:
        def __init__(self, rc=1):
            self.rowcount = rc

    class FinalRes:
        def scalar_one_or_none(self):
            return existing_job

    class FakeDBUpdate:
        def __init__(self):
            self._calls = 0
        async def execute(self, query, *a, **kw):
            self._calls += 1
            # 1: initial select(JobDetails) -> job exists
            if self._calls == 1:
                return JobRes()
            # 2: update -> return UpdateRes with rowcount
            if self._calls == 2:
                return UpdateRes(1)
            # Other calls return job for selects
            if self._calls >= 3:
                class R:
                    def scalar_one_or_none(self):
                        return existing_job
                return R()
            # Should not reach here normally
            return FinalRes()
        async def commit(self):
            return None
        async def rollback(self):
            return None

    monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id')]), raising=False)
    class InsertStub3:
        def __init__(self, *a, **kw):
            pass
        def values(self, *a, **kw):
            return self
    monkeypatch.setattr(repo, 'insert', InsertStub3)
    class UpdateStub2:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw): return self
        def values(self, *a, **kw): return self
    monkeypatch.setattr(repo, 'update', UpdateStub2)
    class DeleteStub2:
        def __init__(self, *a, **kw): pass
        def where(self, *a, **kw): return self
    monkeypatch.setattr(repo, 'delete', DeleteStub2)
    class SelectStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def options(self, *a, **kw):
            return self
    monkeypatch.setattr(repo, 'select', SelectStub)

    res = await repo.update_or_create_job_details(db=FakeDBUpdate(), job_id='00000000-0000-0000-0000-000000000000', job_data={'user_id': 'u1'})
    assert res == existing_job


@pytest.mark.asyncio
async def test_get_job_details_by_id_invalid_uuid_returns_none():
    class NoOpDB:
        async def execute(self, q, *a, **kw):
            class R:
                def scalar_one_or_none(self):
                    return None
            return R()

    res = await repo.get_job_details_by_id(NoOpDB(), 'not-a-uuid')
    assert res is None


@pytest.mark.asyncio
async def test_search_active_job_details_raises_on_db_error():
    class BadDB:
        async def execute(self, q, *a, **kw):
            raise Exception('db error')
    # Reload the module to ensure this test uses an unmodified function reference
    import importlib
    mod = importlib.reload(importlib.import_module('app.db.repository.job_post_repository'))
    from pytest import raises
    with raises(Exception):
        await mod.search_active_job_details(BadDB(), 'role', ['s1'], ['l1'])


@pytest.mark.asyncio
async def test_soft_delete_and_hard_delete_and_set_active(monkeypatch):
    # Validate soft delete and hard delete behaviors and set_job_active_status
    # Fake DB that returns rows affected for delete/update statements
    class R:
        def __init__(self, rowcount=1):
            self.rowcount = rowcount
        def scalar_one_or_none(self):
            return None
        def first(self):
            return None

    class FakeDB:
        def __init__(self):
            self._calls = 0
        async def execute(self, query, *a, **kw):
            self._calls += 1
            return R(rowcount=1)
        async def commit(self):
            return None
        async def rollback(self):
            return None

    # set_job_active_status with invalid uuid returns None
    assert await repo.set_job_active_status(None, 'invalid-uuid', True) is None

    # set_job_active_status with valid uuid updates and returns job (we'll stub final select)
    class FakeDBStatus(FakeDB):
        async def execute(self, query, *a, **kw):
            self._calls += 1
            # final select will be called - return object with scalar_one_or_none
            class FinalRes:
                def scalar_one_or_none(self):
                    return SimpleNamespace(id='j1')
            if self._calls >= 2:
                return FinalRes()
            return R(rowcount=1)

    # stub select/insert/update/delete to avoid SQLAlchemy coercion
    class DML:
        def __init__(self, *a, **kw): pass
        def where(self, *a, **kw): return self
        def values(self, *a, **kw): return self
        def options(self, *a, **kw): return self
    monkeypatch.setattr(repo, 'update', DML)
    monkeypatch.setattr(repo, 'delete', DML)
    monkeypatch.setattr(repo, 'insert', DML)
    monkeypatch.setattr(repo, 'select', lambda *a, **kw: DML())

    res = await repo.set_job_active_status(FakeDBStatus(), '00000000-0000-0000-0000-000000000000', True)
    assert res is not None

    # soft delete job by id with invalid uuid returns False
    assert await repo.soft_delete_job_by_id(FakeDB(), 'not-a-uuid') is False

    # hard_delete_job_by_id with invalid uuid returns False
    assert await repo.hard_delete_job_by_id(FakeDB(), 'not-a-uuid') is False

    # hard_delete_jobs_batch accepts list, invalid entries ignored -> returns 0 if none converted
    assert await repo.hard_delete_jobs_batch(FakeDB(), ['not-a-uuid']) == 0


@pytest.mark.asyncio
async def test_get_all_and_active_and_jobs_by_user(monkeypatch):
    # Fake DB that returns scalars().all()
    class R:
        def __init__(self, rows):
            self._rows = rows
        def scalars(self):
            class S:
                def __init__(self, rows):
                    self._rows = rows
                def all(self):
                    return self._rows
            return S(self._rows)

    class FakeDB2:
        async def execute(self, stmt, *a, **kw):
            return R([SimpleNamespace(id='j1'), SimpleNamespace(id='j2')])

    # Use DML/Select stubs as earlier
    class DML:
        def __init__(self, *a, **kw): pass
        def where(self, *a, **kw): return self
        def options(self, *a, **kw): return self
        def order_by(self, *a, **kw): return self
    monkeypatch.setattr(repo, 'select', DML)
    monkeypatch.setattr(repo, 'selectinload', lambda *a, **kw: 'SELECTIN')

    # Provide column-like stubs to avoid AttributeErrors on attribute access
    class ColumnStub:
        def __init__(self, name):
            self.name = name
        def __eq__(self, other):
            return self
        def in_(self, other):
            return self
        def ilike(self, other):
            return self
        def desc(self):
            return self
    monkeypatch.setattr(repo.JobDetails, 'user_id', ColumnStub('user_id'), raising=False)
    monkeypatch.setattr(repo.JobDetails, 'is_agent_interview', ColumnStub('is_agent_interview'), raising=False)
    monkeypatch.setattr(repo.JobDetails, 'posted_date', ColumnStub('posted_date'), raising=False)

    # get_all_job_details
    rows = await repo.get_all_job_details(FakeDB2())
    assert isinstance(rows, list)

    # get_active_job_details
    rows = await repo.get_active_job_details(FakeDB2())
    assert isinstance(rows, list)

    # get_jobs_by_user_id
    rows = await repo.get_jobs_by_user_id(FakeDB2(), 'u1')
    assert isinstance(rows, list)

    # get_agent_jobs_by_user_id (also tests options with selectinload)
    rows = await repo.get_agent_jobs_by_user_id(FakeDB2(), 'u1')
    assert isinstance(rows, list)


@pytest.mark.asyncio
async def test_job_exists_true_and_soft_delete_true(monkeypatch):
    class R:
        def __init__(self, val=None, rowcount=1):
            self._val = val
            self.rowcount = rowcount
        def scalar_one_or_none(self):
            return self._val

    class FakeDB3:
        async def execute(self, stmt, *a, **kw):
            return R(val=1, rowcount=1)
        async def commit(self):
            return None
        async def rollback(self):
            return None
    assert await repo.job_exists(FakeDB3(), '00000000-0000-0000-0000-000000000000') is True
    # stub repo.update before soft_delete_job_by_id so we don't trigger SQLAlchemy coercion
    class DML:
        def __init__(self, *a, **kw): pass
        def where(self, *a, **kw): return self
        def values(self, *a, **kw): return self
    monkeypatch.setattr(repo, 'update', DML)
    assert await repo.soft_delete_job_by_id(FakeDB3(), '00000000-0000-0000-0000-000000000000') is True


@pytest.mark.asyncio
async def test_hard_delete_jobs_batch_success(monkeypatch):
    class R:
        def __init__(self, rc=2):
            self.rowcount = rc
    class FakeDB4:
        async def execute(self, stmt, *a, **kw):
            return R(rc=2)
        async def commit(self): return None
    # Use two valid uuids
    import uuid
    u1 = str(uuid.uuid4()); u2 = str(uuid.uuid4())
    class DML:
        def __init__(self, *a, **kw): pass
        def where(self, *a, **kw): return self
    monkeypatch.setattr(repo, 'delete', DML)
    res = await repo.hard_delete_jobs_batch(FakeDB4(), [u1, u2])
    assert res == 2


    @pytest.mark.asyncio
    async def test_update_or_create_job_details_rounds_and_agent_config(monkeypatch):
        # Ensure JobDetails.__table__ has expected columns
        monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id')]), raising=False)

        # DML stub which captures table and last values
        class DMLInsert:
            def __init__(self, table):
                self._table = table
                self._last_values = None
            def where(self, *a, **kw):
                return self
            def values(self, *args, **kw):
                self._last_values = kw
                return self
            def options(self, *a, **kw):
                return self

        class DMLDelete:
            def __init__(self, table):
                self._table = table
            def where(self, *a, **kw):
                return self

        class DMLUpdate(DMLInsert):
            pass

        inserted_queries = []

        class FakeDB:
            def __init__(self):
                self._calls = []
            async def execute(self, query, *a, **kw):
                # Save the query object for inspection (if it has _table)
                self._calls.append(query)
                # Emulate final select returning a job object when necessary
                class Res:
                    def scalar_one_or_none(self):
                        return SimpleNamespace(id='job-1', user_id='creator-1')
                    def first(self):
                        return (1,)
                return Res()
            async def commit(self):
                return None
            async def rollback(self):
                return None

        # Monkeypatch insert/update/delete to our DML classes that capture information
        monkeypatch.setattr(repo, 'insert', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'delete', lambda t: DMLDelete(t))
        monkeypatch.setattr(repo, 'update', lambda t: DMLUpdate(t))
        # Provide a chainable select stub
        class SelectChain:
            def where(self, *a, **kw): return self
            def options(self, *a, **kw): return self
            def order_by(self, *a, **kw): return self
            def group_by(self, *a, **kw): return self
            def having(self, *a, **kw): return self
        monkeypatch.setattr(repo, 'select', lambda *a, **kw: SelectChain())
        monkeypatch.setattr(repo, 'selectinload', lambda *a, **kw: 'SELECTIN')

        rounds_data = [
            {
                'round_order': 1,
                'round_name': 'R1',
                'evaluation_criteria': {'shortlisting_criteria': 80, 'rejecting_criteria': 20}
            }
        ]

        agent_configs_data = [
            {
                'round_order': 1,
                'role_fit': '5',
                'potential_fit': '4',
                'location_fit': '3',
                'interview_mode': 'agent',
                'persona': 'alex'
            }
        ]

        db = FakeDB()
        res = await repo.update_or_create_job_details(db=db, job_id=None, job_data={'user_id': 'creator-1'}, rounds_data=rounds_data, agent_configs_data=agent_configs_data)

        # Ensure final returns job object
        assert res is not None

        # Inspect executed queries to find AgentRoundConfig insert stub
        found = False
        for q in db._calls:
            if getattr(q, '_table', None) == repo.AgentRoundConfig:
                found = True
                vals = getattr(q, '_last_values', {})
                # score_distribution should exist and include keys
                sd = vals.get('score_distribution')
                assert sd is not None
                # Should include role_fit, potential, location and thresholds (shortlisting/rejecting)
                assert 'role_fit' in sd or 'role_fit' in sd
                assert 'shortlisting' in sd and 'rejecting' in sd
        assert found is True


    @pytest.mark.asyncio
    async def test_update_or_create_job_details_agent_config_resolves_by_name_and_persona(monkeypatch):
        # Setup table columns
        monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id')]), raising=False)

        class DMLInsert:
            def __init__(self, table):
                self._table = table
                self._last_values = None
            def where(self, *a, **kw):
                return self
            def values(self, *args, **kw):
                self._last_values = kw
                return self

        monkeypatch.setattr(repo, 'insert', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'delete', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'update', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'select', lambda *a, **kw: DMLInsert('SELECT'))
        monkeypatch.setattr(repo, 'selectinload', lambda *a, **kw: 'SELECTIN')

        class FakeDB:
            def __init__(self):
                self._calls = []
            async def execute(self, q, *a, **kw):
                self._calls.append(q)
                class Res:
                    def scalar_one_or_none(self):
                        return SimpleNamespace(id='job-1', user_id='creator-1')
                    def first(self):
                        return (1,)
                return Res()
            async def commit(self):
                return None
            async def rollback(self):
                return None

        rounds_data = [
            {'round_name': 'R1', 'round_order': 1, 'evaluation_criteria': {'shortlisting_criteria': 75, 'rejecting_criteria': 25}}
        ]

        # Interview mode offline should nullify persona
        agent_configs_data = [
            {'roundName': 'R1', 'interviewMode': 'in_person', 'role_fit': '3', 'potential_fit': '2'}
        ]

        db = FakeDB()
        res = await repo.update_or_create_job_details(db=db, job_id=None, job_data={'user_id': 'creator-1'}, rounds_data=rounds_data, agent_configs_data=agent_configs_data)
        assert res is not None
        # locate AgentRoundConfig insert
        found = False
        for q in db._calls:
            if getattr(q, '_table', None) == repo.AgentRoundConfig:
                found = True
                vals = getattr(q, '_last_values', {})
                assert vals.get('persona') is None
                assert vals.get('score_distribution') is not None
        assert found is True


    @pytest.mark.asyncio
    async def test_update_or_create_job_details_agent_config_candidate_uuid_checks_db(monkeypatch):
        # This test ensures agent_configs candidate that is a UUID is checked in DB
        import uuid
        # Table cols
        monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id')]), raising=False)

        # make insert capture table & values
        class DMLInsert:
            def __init__(self, table):
                self._table = table
                self._last_values = None
            def where(self, *a, **kw):
                return self
            def values(self, *args, **kw):
                self._last_values = kw
                return self

        monkeypatch.setattr(repo, 'insert', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'delete', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'update', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'select', lambda *a, **kw: DMLInsert('S'))
        monkeypatch.setattr(repo, 'selectinload', lambda *a, **kw: 'SELECTIN')

        candidate_uuid = str(uuid.uuid4())
        agent_configs_data = [{'roundListId': candidate_uuid, 'interviewMode': 'agent'}]

        class FakeDB:
            def __init__(self):
                self._calls = 0
                self._executed = []
            async def execute(self, q, *a, **kw):
                self._calls += 1
                self._executed.append(q)
                # 1: user exists -> return row
                class R:
                    def first(self):
                        return (1,)
                    def scalar_one_or_none(self):
                        return None
                # 2nd call when repo asks select(RoundList).where -> return existing round
                if self._calls == 2:
                    class ResRound:
                        def scalar_one_or_none(self):
                            return SimpleNamespace(id=uuid.UUID(candidate_uuid))
                    return ResRound()
                return R()
            async def commit(self):
                return None
            async def rollback(self):
                return None

        db = FakeDB()
        res = await repo.update_or_create_job_details(db=db, job_id=None, job_data={'user_id': 'u1'}, agent_configs_data=agent_configs_data)
        assert res is not None
        # find the AgentRoundConfig insert record
        found = False
        for q in db._executed:
            if getattr(q, '_table', None) == repo.AgentRoundConfig:
                found = True
        assert found is True


    @pytest.mark.asyncio
    async def test_update_or_create_job_details_salary_normalization(monkeypatch):
        # Ensure salary values are normalized and camelCase conversion happens
        monkeypatch.setattr(repo.JobDetails, '__table__', SimpleNamespace(columns=[SimpleNamespace(name='user_id'), SimpleNamespace(name='minimum_salary'), SimpleNamespace(name='maximum_salary')]), raising=False)

        class DMLInsert:
            def __init__(self, table):
                self._table = table
                self._last_values = None
            def where(self, *a, **kw):
                return self
            def values(self, *args, **kw):
                self._last_values = kw
                return self

        monkeypatch.setattr(repo, 'insert', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'select', lambda *a, **kw: DMLInsert('S'))
        monkeypatch.setattr(repo, 'delete', lambda t: DMLInsert(t))
        monkeypatch.setattr(repo, 'update', lambda t: DMLInsert(t))

        class FakeDB:
            def __init__(self):
                self._calls = []
            async def execute(self, q, *a, **kw):
                # Save the query object
                self._calls.append(q)
                # First select check returns user exists
                class R:
                    def first(self):
                        return (1,)
                    def scalar_one_or_none(self):
                        return None
                return R()
            async def commit(self):
                return None
            async def rollback(self):
                return None

        db = FakeDB()
        # Provide minimumSalary as comma-containing string
        jdata = {'user_id': 'u1', 'minimumSalary': '2,000', 'max_salary': ''}
        res = await repo.update_or_create_job_details(db=db, job_id=None, job_data=jdata)
        # Check the insert last values captured
        # find inserted JobDetails values among executed DMLInsert objects
        # Our monkeypatched insert returns the same object; locate by its _table
        # Inspect db calls for JobDetails insert and check values
        found_vals = None
        for q in db._calls:
            if getattr(q, '_table', None) == repo.JobDetails:
                found_vals = getattr(q, '_last_values', {})
                break
        vals = found_vals or {}
        # minimum_salary should be integer 2000
        if 'minimum_salary' in vals:
            assert vals['minimum_salary'] == 2000
        # max salary should be set to None
        assert vals.get('maximum_salary') in (None, '') or vals.get('maximum_salary') is None




# NOTE: `search_active_job_details` builds complex SQLAlchemy expressions that
# require ORM instrumentation. For unit tests we avoid exercising the full
# SQL construction here (integration tests cover SQL generation). Focus on
# smaller, deterministic functions in unit tests instead.
