import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
import app.api.v1.job_post_routes as routes_mod
from fastapi import FastAPI
app=FastAPI(); app.include_router(routes_mod.job_post_routes_router)
client=TestClient(app)
payload = {
    "job_id": None,
    "job_title": "t",
    "job_description": "d",
    "minimum_experience": 0,
    "maximum_experience": 0,
    "no_of_openings": 1,
    "active_till": "2025-12-31T00:00:00Z",
    "description_sections": [],
    "skills_required": [{"skill": "Python", "weightage": 5}],
    "job_location": "",
    "role_fit": 0,
    "potential_fit": 0,
    "location_fit": 0,
}
resp = client.post('/job-post/update', json=payload, headers={"X-Test-User":"tester"})
print('STATUS', resp.status_code)
print(resp.text)
