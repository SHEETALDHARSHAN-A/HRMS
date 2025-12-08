import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1.authentication_routes import auth_router, admin_router
import app.controllers.authentication_controller as auth_ctrl

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(auth_router, prefix='/v1')
app.include_router(admin_router, prefix='/v1')

client = TestClient(app)

async def fake_verify_name(token, user_id):
    logger.debug('Inside fake_verify_name')
    return {"success": True}

# monkeypatch by assignment
auth_ctrl.UpdateAdminService.verify_name_update = staticmethod(fake_verify_name)

logger.debug('Sending request')
r = client.get('/v1/admins/verify-name-update?user_id=123&token=tok')
logger.debug('Response status: %s', r.status_code)
logger.debug('Response text: %s', r.text)
print('status', r.status_code)
print('text', r.text)
