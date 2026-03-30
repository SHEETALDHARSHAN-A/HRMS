from fastapi.testclient import TestClient
import main
import app.api.v1.scheduling_routes as sched_mod
from app.db.connection_manager import get_db
from jose import jwt as jose_jwt
import app.db.redis_manager as redis_manager
import app.utils.authentication_utils as auth_utils
from app.schemas.scheduling_interview_request import SchedulingInterviewRequest


def _stub_redis():
    class _DummyRedis:
        def get(self, *args, **kwargs):
            return None
        async def exists(self, *args, **kwargs):
            return False
    return _DummyRedis()


def test_schedule_interview_and_get_scheduled(monkeypatch):
    client = TestClient(main.app)

    async def fake_schedule(request, interview_request, db):
        return {"status_code": 201, "scheduled": True}

    async def fake_get_scheduled(job_id, round_id, db):
        return {"status_code": 200, "items": []}

    async def fake_reschedule(request, reschedule_request, db):
        return {"status_code": 200, "rescheduled": True}

    async def fake_get_db():
        yield None

    monkeypatch.setattr(sched_mod, "scheduling_interview_controller", fake_schedule)
    monkeypatch.setattr(sched_mod, "get_scheduled_interviews_controller", fake_get_scheduled)
    monkeypatch.setattr(sched_mod, "reschedule_interview_controller", fake_reschedule)
    monkeypatch.setitem(main.app.dependency_overrides, get_db, fake_get_db)
    monkeypatch.setattr(redis_manager.RedisManager, "get_client", lambda: _stub_redis())
    import app.authentication.jwt_middleware as jwt_mw
    async def _async_false(jti, r):
        return False
    monkeypatch.setattr(jwt_mw, "is_jti_revoked", _async_false)

    secret = main.app.state.jwt_secret_key
    alg = main.app.state.jwt_algorithm
    payload = {"sub": "sched-user", "jti": "sched-jti-1", "role": "ADMIN"}
    token = jose_jwt.encode(payload, secret, algorithm=alg)

    body = {
        "job_id": "job-1",
        "profile_id": ["p1"],
        "round_id": "r1",
        "interview_date": "2025-12-01",
        "interview_time": "10:00:00"
    }

    resp = client.post("/api/v1/scheduling/schedule-interview", json=body, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json().get("scheduled") is True

    resp2 = client.get("/api/v1/scheduling/scheduled-interviews?job_id=job-1&round_id=r1", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json().get("items") == []

    reschedule_body = {
        "interview_token": "00000000-0000-0000-0000-000000000041",
        "interview_date": "2025-12-05",
        "interview_time": "11:00:00"
    }
    resp3 = client.post("/api/v1/scheduling/reschedule-interview", json=reschedule_body, headers={"Authorization": f"Bearer {token}"})
    assert resp3.status_code == 200
    assert resp3.json().get("rescheduled") is True
