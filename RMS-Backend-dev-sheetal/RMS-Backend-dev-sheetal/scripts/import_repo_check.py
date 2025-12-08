import os
import sys

# Minimal env values to satisfy AppConfig; adjust as needed.
env = {
    "app_base_url": "http://localhost:8000",
    "frontend_url": "http://localhost:3000",
    "frontend_base_url": "http://localhost:3000",
    "redis_host": "localhost",
    "redis_port": "6379",
    "redis_db": "0",
    "openai_api_key": "test",
    "openai_model": "gpt-test",
    "temperature": "0.5",
    "openai_cache": "False",
    "db_name": "testdb",
    "db_user": "testuser",
    "db_password": "testpass",
    "db_host": "localhost",
    "db_port": "5432",
    "db_pool_size": "1",
    "db_max_over_flow": "1",
    "otp_expire_seconds": "300",
    "smtp_server": "smtp.test",
    "smtp_port": "587",
    "smtp_username": "user",
    "smtp_password": "pass",
    "samesite": "Lax",
    "secure": "False",
    "allow_origins": "[]",
    "allow_domains": "[]",
    "secret_key": "secret",
    "algorithm": "HS256",
    "access_token_expire_minutes": "15",
    "access_refresh_token_expire_hours": "24",
    "invite_expire_minutes": "60",
    "invite_expire_seconds": "3600",
    "remember_me_expire_days": "30",
    "report_mail": "report@test.local",
    "default_tenant_id": "default",
    "link_expiration": "3600",
}

os.environ.update(env)

# Add project root to path and import the module
sys.path.insert(0, r"c:\workspace\RMS-B")

try:
    import app.db.repository.user_repository as ur
    print("Imported user_repository ok")
    for name in ("get_user_by_id", "get_user_by_email", "create_user", "update_user_details"):
        print(name, hasattr(ur, name))
except Exception as e:
    print("Import failed:", e)
    raise
