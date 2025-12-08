import asyncio
import re
import pytest
from unittest.mock import AsyncMock
from jose import jwt
from app.utils import authentication_utils as au
from app.config.app_config import AppConfig

settings = AppConfig()

SECRET = settings.secret_key
ALGO = settings.algorithm


def test_generate_otp_code_lengths_and_numeric():
    code = au.generate_otp_code()
    assert code.isdigit()
    assert 4 <= len(code) <= 12

    code2 = au.generate_otp_code(8)
    assert len(code2) == 8


def test_generate_token_and_uuid_format():
    t = au.generate_token()
    assert isinstance(t, str)
    # uuid4-like pattern (hex with dashes)
    assert re.match(r"[0-9a-fA-F\-]{36}", t)


def test_create_access_and_refresh_token_and_get_jti():
    token = au.create_access_token("user1", "ADMIN", first_name="F", last_name="L")
    payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    assert payload["sub"] == "user1"
    assert payload["role"] == "ADMIN"
    assert "jti" in payload

    rtoken = au.create_refresh_token("user2", "HR")
    rpayload = jwt.decode(rtoken, SECRET, algorithms=[ALGO])
    assert rpayload["sub"] == "user2"
    assert rpayload["role"] == "HR"

    # get_jti_from_token should return the jti
    jti = au.get_jti_from_token(token)
    assert jti == payload.get("jti")


@pytest.mark.asyncio
async def test_jti_blocklist_and_revocation(monkeypatch):
    fake_cache = AsyncMock()
    fake_cache.exists = AsyncMock(return_value=True)
    jti = "test-jti"
    # is_jti_revoked should return True when exists returns True
    res = await au.is_jti_revoked(jti, fake_cache)
    assert res is True

    # If cache is None, should return False
    assert await au.is_jti_revoked(jti, None) is False

    # Simulate exception in cache.exists -> should return False (fail-open)
    async def raise_exc(key):
        raise Exception("redis error")
    fake_cache.exists = AsyncMock(side_effect=raise_exc)
    res2 = await au.is_jti_revoked(jti, fake_cache)
    assert res2 is False

    # add_jti_to_blocklist should call set with proper key
    fake_cache.set = AsyncMock()
    await au.add_jti_to_blocklist(jti, fake_cache, 123)
    fake_cache.set.assert_awaited()

    # alias functions should be present
    assert au.add_token_to_blocklist is au.add_jti_to_blocklist
    assert au.is_token_revoked is au.is_jti_revoked
