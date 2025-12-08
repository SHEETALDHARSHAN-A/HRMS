# Debug script to verify send_admin_role_change_email rendering
import sys, types, asyncio

# Ensure repo root is on sys.path so 'app' package can be imported when running from other cwd
if r'c:\workspace\RMS-B' not in sys.path:
    sys.path.insert(0, r'c:\workspace\RMS-B')

# Inject a minimal fake AppConfig to avoid pydantic validation at import time
fake_mod = types.ModuleType('app.config.app_config')
class DummyAppConfig:
    def __init__(self, *a, **k):
        self.app_base_url = 'http://localhost'
        self.frontend_url = 'http://localhost:3000'
        self.frontend_base_url = 'http://localhost:3000'
        self.redis_host = 'localhost'
        self.redis_port = 6379
        self.redis_db = 0
        self.openai_api_key = ''
        self.openai_model = 'gpt-test'
        self.temperature = 0.0
        self.openai_cache = False
        self.db_name = 'test'
        self.db_user = 'user'
        self.db_password = 'pw'
        self.db_host = 'localhost'
        self.db_port = 5432
        self.db_pool_size = 5
        self.db_max_over_flow = 10
        self.otp_expire_seconds = 300
        self.smtp_server = 'localhost'
        self.smtp_port = 25
        self.smtp_username = 'noreply@example.com'
        self.smtp_password = 'pw'
        self.samesite = 'Lax'
        self.secure = False
        self.allow_origins = []
        self.allow_domains = []
        self.secret_key = 'secret'
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = 60
        self.access_refresh_token_expire_hours = 24
        self.invite_expire_minutes = 60
        self.invite_expire_seconds = 3600
        self.remember_me_expire_days = 30
        self.report_mail = 'reports@example.com'
        self.default_tenant_id = 'default'
        self.link_expiration = 3600

fake_mod.AppConfig = DummyAppConfig
sys.modules['app.config.app_config'] = fake_mod

# Now import the email util
from app.utils import email_utils

# Monkeypatch send_email_async to capture subject/body
async def fake_send_email_async(subject, recipient, html_body):
    print('\n=== Captured Email ===')
    print('Subject:', subject)
    print('To:', recipient)
    print('Body snippet:')
    # print a small portion around the performed_by marker
    start = html_body.find('PERFORMED')
    if start == -1:
        print(html_body[:400])
    else:
        print(html_body[max(0,start-200):start+200])
    return True

email_utils.send_email_async = fake_send_email_async

# Run the async send to see rendering
async def main():
    await email_utils.send_admin_role_change_email(
        recipient_email='user@example.com',
        admin_name='Jane Doe',
        old_role='ADMIN',
        new_role='SUPER_ADMIN',
        performed_by='Alice Smith',
        db=None
    )

if __name__ == '__main__':
    asyncio.run(main())
