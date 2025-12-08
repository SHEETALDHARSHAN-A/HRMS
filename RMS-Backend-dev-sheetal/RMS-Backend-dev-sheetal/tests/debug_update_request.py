from fastapi.testclient import TestClient
from types import SimpleNamespace
from main import app as main_app
from app.controllers import job_post_controller as jp_ctrl
from app.db.connection_manager import get_db

async def fake_gen_db():
    class FakeDB:
        async def execute(self, *a, **kw):
            return SimpleNamespace(scalar_one_or_none=lambda: None, all=lambda: [])
        async def commit(self):
            return None
        async def rollback(self):
            return None
    yield FakeDB()

main_app.dependency_overrides[get_db] = fake_gen_db
# Patch UpdateJobPost
class FakeUpdate:
    def __init__(self, db):
        pass
    async def update_job_post(self, job_details, job_id, creator_id):
        return {"success": True, "job_details": {"job_id": "1"}, "status_code": 201}

jp_ctrl.UpdateJobPost = FakeUpdate

client = TestClient(main_app)
payload = {
    "job_id": None,
    "job_title": "Test",
    "job_description": "Testing description",
    "description_sections": [{"title": "Desc", "content": "Test"}],
    "job_location": "Remote",
    "user_id": "user-1",
    "active_till": "2025-12-31T00:00:00Z",
    "skills_required": [{"skill": "python", "weightage": 5}]
}
headers = {"X-Test-User": "user-1"}
resp = client.post('/v1/job-post/update', json=payload, headers=headers)
print('status', resp.status_code)
try:
    print(resp.json())
except Exception as e:
    print('no json', e)
