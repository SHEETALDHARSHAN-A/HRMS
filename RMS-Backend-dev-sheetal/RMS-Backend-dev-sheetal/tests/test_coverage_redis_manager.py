import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as redis
from app.db.redis_manager import RedisManager, safe_set, publish_activation_event, get_redis_client

@pytest.mark.asyncio
async def test_init_pool_and_get_client(monkeypatch):
    # Mock connection pool creation
    mock_from_url = MagicMock()
    monkeypatch.setattr("redis.asyncio.ConnectionPool.from_url", mock_from_url)
    
    # Reset singleton
    RedisManager._pool = None
    
    # Test init
    await RedisManager.init_pool()
    assert RedisManager._pool is not None
    mock_from_url.assert_called_once()
    
    # Test idempotency (call again)
    await RedisManager.init_pool()
    assert mock_from_url.call_count == 1
    
    # Test get_client
    client = RedisManager.get_client()
    assert client is not None

@pytest.mark.asyncio
async def test_get_client_raises_if_uninitialized():
    RedisManager._pool = None
    with pytest.raises(ConnectionError):
        RedisManager.get_client()

@pytest.mark.asyncio
async def test_safe_set_retries_and_failure():
    mock_client = AsyncMock()
    # Simulate ConnectionError for first 2 calls, then success
    mock_client.set.side_effect = [
        ConnectionError("Connection reset"),
        redis.TimeoutError("Timeout"),
        True
    ]
    
    # It should succeed on 3rd try
    res = await safe_set(mock_client, "key", "val")
    assert res is True
    assert mock_client.set.call_count == 3

@pytest.mark.asyncio
async def test_safe_set_failure_after_retries():
    mock_client = AsyncMock()
    # Always fail
    mock_client.set.side_effect = ConnectionError("Redis down")

    res = await safe_set(mock_client, "key", "val", retries=2)
    assert res is False
    assert mock_client.set.call_count == 2

@pytest.mark.asyncio
async def test_publish_activation_event_success():
    mock_client = AsyncMock()
    mock_client.rpush.return_value = 1
    
    res = await publish_activation_event(mock_client, "job-1", "prof-1")
    assert res is True
    mock_client.rpush.assert_called_once()
    
    # Check payload
    args = mock_client.rpush.call_args[0]
    assert args[0] == "activation:queue"
    assert '"job_id": "job-1"' in args[1]

@pytest.mark.asyncio
async def test_publish_activation_event_handles_none_client():
    res = await publish_activation_event(None, "job-1")
    assert res is False

@pytest.mark.asyncio
async def test_get_redis_client_dependency():
    # Should init pool and return client
    with patch.object(RedisManager, 'init_pool', new_callable=AsyncMock) as mock_init:
        with patch.object(RedisManager, 'get_client', return_value="fake_client") as mock_get:
            res = await get_redis_client()
            assert res == "fake_client"
            mock_init.assert_called_once()


# ============================================================================
# Additional Coverage Tests for Missing Lines
# ============================================================================

@pytest.mark.asyncio
async def test_redis_manager_init_pool_no_password():
    """Test RedisManager initialization without password - covers line 38"""
    RedisManager._pool = None
    
    mock_settings = MagicMock()
    mock_settings.redis_password = None  # No password
    mock_settings.redis_host = "localhost"
    mock_settings.redis_port = 6379
    mock_settings.redis_db = 0
    
    with patch('app.db.redis_manager.settings', mock_settings):
        with patch('app.db.redis_manager.redis.ConnectionPool.from_url') as mock_pool:
            await RedisManager.init_pool()
            
            # Verify URL format without password
            call_args = mock_pool.call_args
            redis_url = call_args[0][0]
            assert "redis://localhost:6379/0" in redis_url
            assert "@" not in redis_url  # No auth


@pytest.mark.asyncio
async def test_retry_async_non_retriable_error():
    """Test _retry_async with non-retriable exception - covers lines 79-82"""
    from app.db.redis_manager import _retry_async
    
    async def failing_fn():
        raise ValueError("This is not a retriable error")
    
    with pytest.raises(ValueError) as exc_info:
        await _retry_async(failing_fn, retries=3)
    
    assert "not a retriable error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_publish_activation_event_exception_logged():
    """Test publish_activation_event when exception occurs - covers lines 123-125"""
    mock_client = AsyncMock(spec=redis.Redis)
    mock_client.rpush.side_effect = redis.RedisError("Push failed")
    
    with patch('app.db.redis_manager.logger') as mock_logger:
        result = await publish_activation_event(mock_client, "job123", "profile456")
        
        # Should return False on exception
        assert result is False
        
        # Verify exception was logged
        assert mock_logger.exception.called