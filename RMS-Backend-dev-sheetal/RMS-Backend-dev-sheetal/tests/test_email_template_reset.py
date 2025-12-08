import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_reset_template_to_default_calls_repository_and_returns_true(monkeypatch):
    # Provide a lightweight fake AppConfig module before importing service to avoid pydantic validation at import-time
    import types, sys
    fake_mod = types.ModuleType('app.config.app_config')
    class DummyAppConfig:
        def __init__(self, *a, **k):
            # minimal set of attributes used across imports
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

    # Import inside test to avoid top-level AppConfig initialization during collection
    from app.services.config_service.email_template_service import EmailTemplateService

    # Arrange
    async def fake_save_or_update(db, key, subj, body):
        # emulate success
        return None

    monkeypatch.setattr(
        'app.services.config_service.email_template_service.ConfigRepository.save_or_update_email_template',
        fake_save_or_update
    )

    # Act
    # We pass a dummy object for db since repository is monkeypatched
    result = await EmailTemplateService.reset_template_to_default(db=object(), template_key='OTP')

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_reset_template_to_default_returns_false_for_unknown_key():
    import types, sys
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

    from app.services.config_service.email_template_service import EmailTemplateService

    result = await EmailTemplateService.reset_template_to_default(db=object(), template_key='UNKNOWN_KEY')
    assert result is False
