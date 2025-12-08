import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from main import lifespan

@pytest.mark.asyncio
async def test_lifespan_startup():
    app = FastAPI()
    
    with patch("main.init_db", new_callable=AsyncMock) as mock_db_init:
        with patch("main.RedisManager.init_pool", new_callable=AsyncMock) as mock_redis_init:
            # `lifespan` is an async generator; drive it to the first yield to run startup
            agen = lifespan(app)
            await agen.__anext__()
            mock_db_init.assert_awaited_once()
            mock_redis_init.assert_awaited_once()
            # close the async generator
            await agen.aclose()