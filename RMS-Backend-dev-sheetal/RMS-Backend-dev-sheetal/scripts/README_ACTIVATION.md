Activation worker and event-driven activation

What was added
- `scripts/activation_worker.py` — an async worker that connects to Redis, consumes events from the `activation:queue`, and evaluates jobs using the existing activation manager logic.
- `app/db/redis_manager.py` — added `ACTIVATION_QUEUE_KEY` and `publish_activation_event` helper.
- `app/services/job_post/activation_hook.py` — a small helper to call the publish helper from your application code when a candidate is shortlisted.
- `app/config/app_config.py` — added `internal_service_token` config value for protecting internal endpoints.
- `app/api/v1/job_post_routes.py` — evaluate endpoint now requires the `X-Internal-Token` header to be set to the configured `internal_service_token`.

How to use

1. Ensure `.env` has Redis and DB config and (optionally) set `INTERNAL_SERVICE_TOKEN` to a random secret.

2. Start the activation worker (recommended to run separately from FastAPI server):

```powershell
# from repository root, in your Python venv
python -m scripts.activation_worker
```

3. In the code path that marks a profile as shortlisted, call the publish helper so the worker evaluates the job immediately. Example:

```python
# inside the code that updates Profile.curated_results to 'shortlisted'
from app.db.redis_manager import get_redis_client
from app.services.job_post.activation_hook import notify_shortlist_event

redis_client = await get_redis_client()
await notify_shortlist_event(redis_client, job_id, profile_id)
```

4. The worker will pop events and call `evaluate_and_deactivate_job` directly so deactivation is applied in the DB session. This avoids extra HTTP calls and keeps logic local.

Alternative: If you prefer the worker to call the HTTP endpoint, set `INTERNAL_SERVICE_TOKEN` and have the worker POST to `/api/v1/job-post/{job_id}/evaluate-activation` with the header `X-Internal-Token: <your token>`.

Notes & production suggestions
- Run the worker as a separate managed service (systemd, supervisor, Docker container, or Kubernetes deployment). Don't run it inside the FastAPI Uvicorn process in production.
- Make sure `INTERNAL_SERVICE_TOKEN` is set in a secure environment variable store and not checked into source control.
- Add retry/backoff and DLQ for malformed or repeatedly failing events if you expect heavy throughput.
- If you want at-least-once semantics, consider using Redis Streams instead of a plain list.
