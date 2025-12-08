from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1.config_routes import router as config_router
from app.services.config_service.email_template_service import EmailTemplateService

app = FastAPI()
app.include_router(config_router, prefix='/v1')
client = TestClient(app)

async def fake_reset(db, template_key):
    print('fake_reset called with', template_key)
    return template_key == 'FOUND'

# monkeypatch by assignment
EmailTemplateService.reset_template_to_default = fake_reset

r = client.post('/v1/config/email/template/NOTFOUND/reset')
print('status', r.status_code)
print('body', r.text)

r2 = client.post('/v1/config/email/template/FOUND/reset')
print('status2', r2.status_code)
print('body2', r2.text)
