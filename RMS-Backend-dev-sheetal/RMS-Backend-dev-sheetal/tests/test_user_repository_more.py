import pytest
from types import SimpleNamespace
from app.db.repository import user_repository as repo


class Res:
    def __init__(self, rows=None, first=None, scalar=None):
        self._rows = rows or []
        self._first = first
        self._scalar = scalar

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
    def first(self):
        # For scalars().first() path, prefer scalar value if present,
        # otherwise return explicit first tuple or first row from list.
        if self._scalar is not None:
            return self._scalar
        if self._first is not None:
            return self._first
        if self._rows:
            return self._rows[0]
        return None


@pytest.mark.asyncio
async def test_create_user_and_get_by_id():
    class FakeUser:
        def __init__(self):
            self.user_id = 'u1'
            self.email = 'a@b.com'

    class FakeDB:
        def __init__(self):
            self.added = None
            self.committed = False
            self.refreshed = False

        def add(self, u):
            self.added = u

        async def commit(self):
            self.committed = True

        async def refresh(self, u):
            self.refreshed = True

        async def execute(self, q, *a, **kw):
            return Res(scalar=FakeUser())

    user = FakeUser()
    r = await repo.create_user(FakeDB(), user)
    assert r == user

    # get_user_by_id returns None when not found
    class FaDB2:
        async def execute(self, q, *a, **kw):
            return Res(scalar=None)

    assert await repo.get_user_by_id(FaDB2(), 'not-found') is None


@pytest.mark.asyncio
async def test_get_user_by_email_programming_error_and_success(monkeypatch):
    # Success path
    class FakeDB:
        async def execute(self, q, *a, **kw):
            return Res(scalar=SimpleNamespace(user_id='u1', email='a@b.com'))

    assert await repo.get_user_by_email(FakeDB(), 'A@B.COM') is not None

    # ProgrammingError -> fallback path
    class ProgDB:
        class Err:
            pass

        async def execute(self, q, *a, **kw):
            # Simulate initial ilike select raising ProgrammingError
            # SQLAlchemy DBAPIError/ProgrammingError expects (statement, params, orig) args
            raise repo.ProgrammingError('stmt', {}, Exception('oops'))

        async def rollback(self):
            return None

    # Monkeypatch the fallback execute to return known columns
    class ProgDB2(ProgDB):
        async def execute(self, q, *a, **kw):
            # First call raises
            if getattr(self, '_called', False) is False:
                self._called = True
                raise repo.ProgrammingError('stmt', {}, Exception('oops'))
            return Res(first=('u1', 'First', 'Last', 'a@b.com', 'ADMIN', None, None))

        async def rollback(self):
            return None

    r = await repo.get_user_by_email(ProgDB2(), 'a@b.com')
    assert r is not None
    assert r.email == 'a@b.com'


@pytest.fixture(autouse=True)
def patch_sqlalchemy(monkeypatch):
    class SelectStub:
        def __init__(self, *a, **kw):
            pass
        def where(self, *a, **kw):
            return self
        def options(self, *a, **kw):
            return self
        def label(self, *a, **kw):
            return self
        def limit(self, *a, **kw):
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
    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)
    monkeypatch.setattr(repo, 'update', UpdateStub, raising=False)
    monkeypatch.setattr(repo, 'delete', DeleteStub, raising=False)


@pytest.mark.asyncio
async def test_get_all_admins_details_roles(monkeypatch):
    class FakeDB:
        def __init__(self, rows):
            self.rows = rows

        async def execute(self, q, *a, **kw):
            return Res(rows=self.rows)

    rows = [
        ('u1', 'A', 'X', 'a@b', '123', 'ADMIN', SimpleNamespace(isoformat=lambda: '2025-01-01')),
        ('u2', 'B', 'Y', 'b@b', '456', 'HR', SimpleNamespace(isoformat=lambda: '2025-01-02')),
    ]
    db = FakeDB(rows)

    res_super = await repo.get_all_admins_details(db, 'SUPER_ADMIN')
    assert len(res_super) == 2

    db2 = FakeDB(rows)
    res_admin = await repo.get_all_admins_details(db2, 'ADMIN')
    assert len(res_admin) == 2

    db3 = FakeDB(rows)
    res_hr = await repo.get_all_admins_details(db3, 'HR')
    assert len(res_hr) == 2

    # Unknown role -> []
    db4 = FakeDB(rows)
    res_unknown = await repo.get_all_admins_details(db4, 'UNKNOWN')
    assert res_unknown == []


@pytest.mark.asyncio
async def test_search_admins_returns_empty_and_results(monkeypatch):
    class FakeDB:
        def __init__(self, rows):
            self.rows = rows

        async def execute(self, q, *a, **kw):
            return Res(rows=self.rows)

    assert await repo.search_admins(FakeDB([]), '') == []

    rows = [
        ('u1', 'A', 'X', 'a@b', '123', 'ADMIN', SimpleNamespace(isoformat=lambda: '2025-01-01')), 
    ]
    db = FakeDB(rows)
    res = await repo.search_admins(db, 'A')
    assert len(res) == 1


@pytest.mark.asyncio
async def test_delete_users_and_update_user_details(monkeypatch):
    # delete_users_by_id_and_type: when no users matched, return (0, [])
    class FakeDBNo:
        async def execute(self, q, *a, **kw):
            return Res(rows=[])

    assert await repo.delete_users_by_id_and_type(FakeDBNo(), ['u1']) == (0, [])

    # When users matched and delete returns rowcount
    class FakeDelDB:
        def __init__(self):
            self._rows = [SimpleNamespace(user_id='u1', first_name='A', last_name='X', email='a@b', phone_number='123', role='ADMIN', created_at=SimpleNamespace(isoformat=lambda: '2025-01-01'))]
            self.commit_called = False

        async def execute(self, q, *a, **kw):
            if str(q).lower().startswith('delete'):
                class R:
                    rowcount = 1
                return R()
            return Res(rows=self._rows)

        async def commit(self):
            self.commit_called = True

    db = FakeDelDB()
    cnt, users = await repo.delete_users_by_id_and_type(db, ['u1'], allowed_roles=['ADMIN'], caller_role='SUPER_ADMIN')
    assert cnt == 1
    assert users and users[0].user_id == 'u1'

    # update_user_details - when no updates -> None
    class FakeDBu:
        async def execute(self, q, *a, **kw):
            return Res(scalar=SimpleNamespace(user_id='u1'))

        async def commit(self):
            return None

    assert await repo.update_user_details(FakeDBu(), 'u1', {}) is None

    # update_user_details normal path
    class FakeDBUpdate(FakeDBu):
        async def execute(self, q, *a, **kw):
            if str(q).lower().startswith('update'):
                return Res()
            return Res(scalar=SimpleNamespace(user_id='u1'))

    res = await repo.update_user_details(FakeDBUpdate(), 'u1', {'first_name': 'New'})
    assert res is not None
