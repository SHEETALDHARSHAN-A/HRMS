import pytest
from types import SimpleNamespace
from datetime import datetime, timedelta
import asyncio

from app.db.repository import notification_repository as repo


# Helper stubs to avoid SQLAlchemy coercion in repository tests
class SelectStub:
    def __init__(self, *a, **kw):
        pass

    def where(self, *a, **kw):
        return self

    def order_by(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

class UpdateStub:
    def __init__(self, *a, **kw):
        pass

    def where(self, *a, **kw):
        return self

    def values(self, *a, **kw):
        return self


@pytest.fixture(autouse=True)
def patch_sqlalchemy(monkeypatch):
    """Patch SQLAlchemy helpers used in the repository to avoid coercion errors
    in unit tests where we use dummy SimpleNamespace objects instead of real
    SQLAlchemy models and columns.
    """
    monkeypatch.setattr(repo, 'select', SelectStub, raising=False)
    monkeypatch.setattr(repo, 'update', UpdateStub, raising=False)
    # and_ and or_ are used by invitation stats — make them no-ops returning a tuple
    monkeypatch.setattr(repo, 'and_', lambda *a, **kw: a, raising=False)
    monkeypatch.setattr(repo, 'or_', lambda *a, **kw: a, raising=False)


@pytest.mark.asyncio
async def test_fetch_notifications_unread_and_all():
    # Prepare fake notifications
    n1 = SimpleNamespace(notification_id='n1', user_id='u1', is_read=False)
    n2 = SimpleNamespace(notification_id='n2', user_id='u1', is_read=True)

    class ResultAll:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeDB:
        async def execute(self, q, *a, **kw):
            return ResultAll([n1, n2])

    fake_db = FakeDB()

    # unread_only False returns both
    res = await repo.fetch_notifications(fake_db, 'u1', unread_only=False, limit=10)
    assert res == [n1, n2]

    # unread_only True returns filtered list (our fake DB returns same list; ensure the method handles the flag usage)
    # For this test we simulate DB returning only unread rows
    class FakeDBUnread:
        async def execute(self, q, *a, **kw):
            return ResultAll([n1])

    res_unread = await repo.fetch_notifications(FakeDBUnread(), 'u1', unread_only=True, limit=10)
    assert res_unread == [n1]


@pytest.mark.asyncio
async def test_fetch_user_by_id_found_and_not_found():
    class ResFound:
        def scalar_one_or_none(self):
            return SimpleNamespace(user_id='u1')

    class ResNotFound:
        def scalar_one_or_none(self):
            return None

    class FakeDB:
        def __init__(self, found=True):
            self._found = found

        async def execute(self, q, *a, **kw):
            return ResFound() if self._found else ResNotFound()

    assert await repo.fetch_user_by_id(FakeDB(found=True), 'u1') is not None
    assert await repo.fetch_user_by_id(FakeDB(found=False), 'u1') is None


@pytest.mark.asyncio
async def test_mark_notification_read_db_found_and_not_found():
    # Case: not found -> should return False
    class ResNone:
        def scalar_one_or_none(self):
            return None

    class FakeDBNotFound:
        async def execute(self, q, *a, **kw):
            return ResNone()

    assert await repo.mark_notification_read_db(FakeDBNotFound(), 'n1', 'u1') is False

    # Case: found -> should set is_read True and record commit
    class NotificationObj:
        def __init__(self):
            self.notification_id = 'n1'
            self.user_id = 'u1'
            self.is_read = False
            self.read_at = None

    notif = NotificationObj()

    class ResFound:
        def __init__(self, obj):
            self._obj = obj

        def scalar_one_or_none(self):
            return self._obj

    class FakeDBFound:
        def __init__(self, obj):
            self.obj = obj
            self.committed = False

        async def execute(self, q, *a, **kw):
            return ResFound(self.obj)

        async def commit(self):
            self.committed = True

    fake_db = FakeDBFound(notif)

    res = await repo.mark_notification_read_db(fake_db, 'n1', 'u1')
    assert res is True
    assert notif.is_read is True
    assert notif.read_at is not None
    assert fake_db.committed is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read_db_rowcount_and_exception():
    # Happy path: rowcount present as 3
    class ResRow:
        def __init__(self):
            self.rowcount = 3

    class FakeDB:
        async def execute(self, q, *a, **kw):
            return ResRow()

        async def commit(self):
            return None

    assert await repo.mark_all_notifications_read_db(FakeDB(), 'u1') == 3

    # Exception path: rowcount raising error -> should return 0
    class ResBadRow:
        @property
        def rowcount(self):
            raise Exception("boom")

    class FakeDBBad:
        async def execute(self, q, *a, **kw):
            return ResBadRow()

        async def commit(self):
            return None

    assert await repo.mark_all_notifications_read_db(FakeDBBad(), 'u1') == 0


@pytest.mark.asyncio
async def test_get_unread_count_db_returns_len():
    class Res:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeDB:
        async def execute(self, q, *a, **kw):
            return Res([1, 2, 3])

    assert await repo.get_unread_count_db(FakeDB(), 'u1') == 3


@pytest.mark.asyncio
async def test_delete_notification_db_found_and_not_found():
    # Not found
    class ResNone:
        def scalar_one_or_none(self):
            return None

    class FakeDBNotFound:
        async def execute(self, q, *a, **kw):
            return ResNone()

    assert await repo.delete_notification_db(FakeDBNotFound(), 'n1', 'u1') is False

    # Found
    class NotificationObj:
        def __init__(self):
            self.notification_id = 'n1'
            self.user_id = 'u1'

    notif = NotificationObj()

    class ResFound:
        def __init__(self, obj):
            self.obj = obj

        def scalar_one_or_none(self):
            return self.obj

    class FakeDBFound:
        def __init__(self, obj):
            self.obj = obj
            self.deleted = False
            self.committed = False

        async def execute(self, q, *a, **kw):
            return ResFound(self.obj)

        async def delete(self, o):
            self.deleted = True

        async def commit(self):
            self.committed = True

    fake_db = FakeDBFound(notif)
    assert await repo.delete_notification_db(fake_db, 'n1', 'u1') is True
    assert fake_db.deleted is True
    assert fake_db.committed is True


@pytest.mark.asyncio
async def test_fetch_invitations_by_inviter_and_get_invitation_stats_db():
    # fetch_invitations_by_inviter
    inv1 = SimpleNamespace(invitation_id='i1', invited_by='u1', status='PENDING')
    inv2 = SimpleNamespace(invitation_id='i2', invited_by='u1', status='ACCEPTED')

    class ResAll:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeDB:
        def __init__(self, rows):
            self.rows = rows

        async def execute(self, q, *a, **kw):
            return ResAll(self.rows)

    # Default (no filter) returns both
    r = await repo.fetch_invitations_by_inviter(FakeDB([inv1, inv2]), 'u1')
    assert r == [inv1, inv2]

    # Filtered returns only one
    r2 = await repo.fetch_invitations_by_inviter(FakeDB([inv1]), 'u1', status_filter='PENDING')
    assert r2 == [inv1]

    # get_invitation_stats_db: return pending, accepted, expired numbers based on returns for three queries
    class FakeDBStats:
        def __init__(self):
            self._calls = 0

        async def execute(self, q, *a, **kw):
            self._calls += 1
            if self._calls == 1:
                # pending
                return ResAll([inv1])
            if self._calls == 2:
                # accepted
                return ResAll([inv2])
            # expired
            return ResAll([])

    stats = await repo.get_invitation_stats_db(FakeDBStats(), 'u1')
    assert stats['pending'] == 1
    assert stats['accepted'] == 1
    assert stats['expired'] == 0
