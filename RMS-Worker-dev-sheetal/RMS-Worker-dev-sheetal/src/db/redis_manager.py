# src/db/redis_manager.py

import redis.asyncio as redis
from src.config.app_config import AppConfig

settings = AppConfig()

JWT_BLOCKLIST_KEY = "jwt:jti_blocklist:"

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
        """Returns a Redis client instance from the initialized pool."""
        if cls._pool is None:
            raise ConnectionError("Redis pool not initialized. Call init_pool() first.")
        return redis.Redis(connection_pool=cls._pool)

async def get_redis_client():
    """Dependency injector for getting an active Redis client (used in routes/controllers)."""
    await RedisManager.init_pool()
    return RedisManager.get_client()

SIGNUP_CACHE_PREFIX = "signup_user:"
ACTIVATION_QUEUE_KEY = "activation:queue"

import json

async def publish_activation_event(redis_client, job_id: str, profile_id: str | None = None):
    """Push a simple activation event into Redis so a worker can evaluate it.

    Event payload (JSON string) contains at least `job_id`. `profile_id` is optional.
    Uses a right-push so workers can use BRPOP to consume.
    """
    if redis_client is None:
        raise ConnectionError("Redis client is None")

    payload = {"job_id": job_id}
    if profile_id:
        payload["profile_id"] = profile_id

    try:
        await redis_client.rpush(ACTIVATION_QUEUE_KEY, json.dumps(payload))
        return True
    except Exception as e:
        # Keep this lightweight; caller may log.
        raise
