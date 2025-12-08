import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from app.db.repository.config_repository import ConfigRepository


class Result:
    def __init__(self, scalar=None, scalar_or_none=None):
        self._scalar = scalar
        self._scalar_none = scalar_or_none

    def scalar_one_or_none(self):
        return self._scalar_none

    def scalar_one(self):
        return self._scalar


class FakeDB:
    def __init__(self, result=None, raise_exc=False):
        self._result = result or Result()
        self._raise = raise_exc

    async def execute(self, stmt):
        if self._raise:
            raise Exception("DB error")
        return self._result

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_get_template_by_key_exact_match():
    record = SimpleNamespace(template_key="k", subject_template="S", body_template_html="B")
    result = Result(scalar_or_none=record)
    db = FakeDB(result=result)
    # Avoid SQLAlchemy coercion; stub select to simple no-op builder
    from app.db.repository import config_repository
    config_repository.select = lambda *a, **k: SimpleNamespace(where=lambda *a, **k: "stmt")
    out = await ConfigRepository.get_template_by_key(db, "k")
    assert out is record


@pytest.mark.asyncio
async def test_get_template_by_key_case_insensitive_and_alt_key():
    # first None, then case-insensitive match
    record2 = SimpleNamespace(template_key="K2", subject_template="S2", body_template_html="B2")
    # We will simulate execute returning None first then record by swapping db's _result
    class DBTwo(FakeDB):
        def __init__(self):
            self.calls = 0
        async def execute(self, stmt):
            self.calls += 1
            if self.calls == 1:
                return Result(scalar_or_none=None)
            if self.calls == 2:
                return Result(scalar_or_none=record2)
            return Result(scalar_or_none=None)

    db = DBTwo()
    from app.db.repository import config_repository
    config_repository.select = lambda *a, **k: SimpleNamespace(where=lambda *a, **k: "stmt")
    out = await ConfigRepository.get_template_by_key(db, "k2")
    assert out is record2


@pytest.mark.asyncio
async def test_get_template_by_key_alt_key_normalization():
    rec = SimpleNamespace(template_key="ALT", subject_template="SA", body_template_html="BA")
    class DBThree(FakeDB):
        def __init__(self):
            self.calls = 0
        async def execute(self, stmt):
            self.calls += 1
            # first two calls return None; 3rd returns normalized key record
            if self.calls < 3:
                return Result(scalar_or_none=None)
            return Result(scalar_or_none=rec)

    db = DBThree()
    from app.db.repository import config_repository
    config_repository.select = lambda *a, **k: SimpleNamespace(where=lambda *a, **k: "stmt")
    out = await ConfigRepository.get_template_by_key(db, "ALT-KEY")
    assert out is rec


@pytest.mark.asyncio
async def test_get_template_by_key_error_returns_none():
    db = FakeDB(raise_exc=True)
    from app.db.repository import config_repository
    config_repository.select = lambda *a, **k: SimpleNamespace(where=lambda *a, **k: "stmt")
    res = await ConfigRepository.get_template_by_key(db, "any")
    assert res is None


@pytest.mark.asyncio
async def test_save_or_update_email_template_update_path(monkeypatch):
    # Simulate existing template; ConfigRepository.get_template_by_key returns record
    existing = SimpleNamespace(template_key="k", subject_template="S", body_template_html="B")
    monkeypatch.setattr(ConfigRepository, "get_template_by_key", AsyncMock(return_value=existing))
    # Simulate db execute returning an update result
    class DB(FakeDB):
        async def execute(self, stmt):
            return Result()
    db = DB()
    from app.db.repository import config_repository
    # stub update to not use SQLAlchemy internals
    config_repository.update = lambda *a, **k: SimpleNamespace(where=lambda *a, **k: SimpleNamespace(values=lambda **k: "ok"))
    # The function will return whatever get_template_by_key returns after update
    res = await ConfigRepository.save_or_update_email_template(db, "k", "Sx", "Bx")
    assert res is existing


@pytest.mark.asyncio
async def test_save_or_update_email_template_insert_path(monkeypatch):
    # No existing template
    monkeypatch.setattr(ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    record = SimpleNamespace(template_key="knew", subject_template="S1", body_template_html="B1")
    class DB(FakeDB):
        async def execute(self, stmt):
            return Result(scalar=record)
    db = DB()
    from app.db.repository import config_repository
    # stub insert to avoid SQLAlchemy coercion
    config_repository.insert = lambda *a, **k: SimpleNamespace(values=lambda **k: SimpleNamespace(returning=lambda *a, **k: "r"))
    res = await ConfigRepository.save_or_update_email_template(db, "knew", "S1", "B1")
    assert res is record
