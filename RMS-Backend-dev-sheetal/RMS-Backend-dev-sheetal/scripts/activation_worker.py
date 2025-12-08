# scripts/activation_worker.py

"""
Activation worker that consumes activation events from Redis and evaluates each job
by calling the activation manager directly (so everything runs in the same process
and DB session).

Usage:
  python -m scripts.activation_worker

This requires the same virtualenv as the app and access to the project's .env for DB/Redis.
"""
import json
import asyncpg
import asyncio
import traceback

from app.config.app_config import AppConfig
from app.db.connection_manager import AsyncSessionLocal
from app.db.redis_manager import RedisManager, ACTIVATION_QUEUE_KEY

async def _process_event(job_id: str, profile_id: str | None = None):
    """Run activation evaluation for a job with a fresh DB session."""
    from app.services.job_post.activation_manager import evaluate_and_deactivate_job
    from app.db.repository.job_post_repository import get_job_details_by_id

    async with AsyncSessionLocal() as session:
        try:
            job = await get_job_details_by_id(session, job_id)
            if not job:
                print(f"[activation_worker] job {job_id} not found")
                return

            changed = await evaluate_and_deactivate_job(session, job)
            print(f"[activation_worker] evaluated job={job_id} deactivated={changed} (profile={profile_id})")
        except Exception as e:
            print(f"[activation_worker] error evaluating job {job_id}: {e}")
            traceback.print_exc()


async def _consume_redis(redis_client):
    """Fallback consumer that drains Redis list events (BRPOP)."""
    print("[activation_worker] connected to redis, waiting for list events...")
    while True:
        try:
            item = await redis_client.brpop(ACTIVATION_QUEUE_KEY, timeout=1)
            if not item:
                await asyncio.sleep(0.5)
                continue

            _, raw = item
            try:
                payload = json.loads(raw)
            except Exception:
                print(f"[activation_worker] invalid payload: {raw}")
                continue

            job_id = payload.get("job_id")
            profile_id = payload.get("profile_id")
            if not job_id:
                print("[activation_worker] missing job_id in payload")
                continue

            await _process_event(job_id, profile_id)

        except Exception as e:
            print(f"[activation_worker] redis loop error: {e}")
            traceback.print_exc()
            await asyncio.sleep(2)


async def _listen_postgres_notifications(dsn: str):
    """Listen for Postgres NOTIFY messages on channel 'profile_shortlisted'.

    When a notification arrives, payload is expected to be a JSON string with
    keys 'job_id' and 'profile_id'. We schedule `_process_event` on the loop.
    """
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        print(f"[activation_worker] could not connect to Postgres for LISTEN: {e}")
        return

    async def _callback(_connection, pid, _channel, payload):
        try:
            data = json.loads(payload)
        except Exception:
            print(f"[activation_worker] invalid pg notify payload: {payload}")
            return

        job_id = data.get("job_id")
        profile_id = data.get("profile_id")
        if not job_id:
            print("[activation_worker] notify missing job_id")
            return

        # schedule processing in the event loop
        asyncio.create_task(_process_event(job_id, profile_id))

    await conn.add_listener('profile_shortlisted', _callback)
    await conn.execute('LISTEN profile_shortlisted;')

    print('[activation_worker] listening on Postgres channel profile_shortlisted')

    try:
        # Keep the connection open; callbacks will run on notifications
        while True:
            await asyncio.sleep(60)
    finally:
        await conn.close()


async def main():
    cfg = AppConfig()

    # Init redis pool and postgres listener in parallel
    await RedisManager.init_pool()
    redis_client = RedisManager.get_client()

    # Build DSN for asyncpg
    pg_dsn = f"postgresql://{cfg.db_user}:{cfg.db_password}@{cfg.db_host}:{cfg.db_port}/{cfg.db_name}"

    # Run both listeners concurrently
    await asyncio.gather(
        _consume_redis(redis_client),
        _listen_postgres_notifications(pg_dsn)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[activation_worker] shutting down")
