# app/db/redis_manager.py

import asyncio
import json
import logging
import time
import redis.asyncio as redis
from app.config.app_config import AppConfig
from pydantic_core import _pydantic_core

try:
    settings = AppConfig()
except Exception:
    # In test environments AppConfig may be missing env vars; fall back to None
    settings = None

JWT_BLOCKLIST_KEY = "jwt:jti_blocklist:"

logger = logging.getLogger(__name__)


class RedisManager:
    _pool: redis.ConnectionPool | None = None

    @classmethod
    async def init_pool(cls):
        """Initializes the async connection pool for Redis (idempotent).

        Adds a small socket timeout, keepalive and retry_on_timeout to help
        reduce intermittent remote-closed errors. Call this on app startup.
        """
        if cls._pool is None:
            redis_password = getattr(settings, "redis_password", None)

            if redis_password:
                redis_url = f"redis://:{redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            else:
                redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

            cls._pool = redis.ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
                health_check_interval=30,
                max_connections=20,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
            )

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Returns a Redis client instance using the initialized pool."""
        if cls._pool is None:
            raise ConnectionError("Redis pool not initialized. Call init_pool() first.")
        return redis.Redis(connection_pool=cls._pool)


async def get_redis_client():
    """Dependency injector for getting an active Redis client (used in routes/controllers)."""
    await RedisManager.init_pool()
    return RedisManager.get_client()


SIGNUP_CACHE_PREFIX = "signup_user:"
ACTIVATION_QUEUE_KEY = "activation:queue"


async def _retry_async(fn, retries: int = 3, backoff: float = 0.5, *args, **kwargs):
    """Helper to retry async redis operations with exponential backoff."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return await fn(*args, **kwargs)
        except (redis.ConnectionError, redis.TimeoutError, ConnectionError) as exc:
            last_exc = exc
            wait = backoff * (2 ** (attempt - 1))
            logger.warning("Redis operation failed (attempt %s/%s): %s — retrying in %.2fs", attempt, retries, exc, wait)
            await asyncio.sleep(wait)
        except Exception as exc:
            # Non-retriable error
            logger.exception("Redis unexpected error: %s", exc)
            raise
    # If we reach here, all retries failed
    raise last_exc


async def safe_set(redis_client, key: str, value, ex: int | None = None, nx: bool = False, retries: int = 3):
    """Set a key in Redis with retries. Returns True on success, False otherwise."""
    if redis_client is None:
        logger.error("safe_set called with None redis_client for key=%s", key)
        return False

    async def _op():
        return await redis_client.set(key, value, ex=ex, nx=nx)

    try:
        return await _retry_async(_op, retries=retries)
    except Exception as exc:
        logger.error("Failed to set key %s in Redis after %s retries: %s", key, retries, exc)
        return False


async def publish_activation_event(redis_client, job_id: str, profile_id: str | None = None):
    """Push a simple activation event into Redis so a worker can evaluate it.

    Event payload (JSON string) contains at least `job_id`. `profile_id` is optional.
    Uses a right-push so workers can use BRPOP to consume.
    """
    if redis_client is None:
        logger.error("publish_activation_event: redis_client is None")
        return False

    payload = {"job_id": job_id}
    if profile_id:
        payload["profile_id"] = profile_id

    async def _op():
        return await redis_client.rpush(ACTIVATION_QUEUE_KEY, json.dumps(payload))

    try:
        await _retry_async(_op, retries=3)
        return True
    except Exception as e:
        logger.exception("Failed to publish activation event to Redis: %s", e)
        return False
