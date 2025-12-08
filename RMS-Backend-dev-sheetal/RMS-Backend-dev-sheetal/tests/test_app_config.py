import app.config.app_config as app_config


def _minimal_config_kwargs():
    # Provide minimal required fields with safe dummy values
    return {
        "app_base_url": "http://api.local",
        "frontend_url": "http://front.local",
        "frontend_base_url": "http://front-base.local",
        "redis_host": "127.0.0.1",
        "redis_port": "6379",
        "redis_db": "0",
        "openai_api_key": "key",
        "openai_model": "gpt-x",
        "temperature": 0.5,
        "openai_cache": False,
        "db_name": "db",
        "db_user": "u",
        "db_password": "p",
        "db_host": "localhost",
        "db_port": "5432",
        "db_pool_size": "1",
        "db_max_over_flow": "1",
        "otp_expire_seconds": 60,
        "smtp_server": "smtp",
        "smtp_port": 25,
        "smtp_username": "s",
        "smtp_password": "p",
        "samesite": "Lax",
        "secure": False,
        "allow_origins": ["*"],
        "allow_domains": ["example.com"],
        "secret_key": "sk",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "access_refresh_token_expire_hours": 24,
        "invite_expire_minutes": 10,
        "invite_expire_seconds": 600,
        "remember_me_expire_days": 7,
        "report_mail": "report@example.com",
        "default_tenant_id": "t1",
        "link_expiration": 3600,
    }


def test_get_frontend_url_prefers_frontend_url():
    cfg = app_config.AppConfig(**_minimal_config_kwargs())
    assert cfg.get_frontend_url == "http://front.local"


def test_get_frontend_url_falls_back_to_base():
    kw = _minimal_config_kwargs()
    kw["frontend_url"] = ""  # falsy -> should fall back
    cfg = app_config.AppConfig(**kw)
    assert cfg.get_frontend_url == "http://front-base.local"


def test_get_api_and_base_url():
    cfg = app_config.AppConfig(**_minimal_config_kwargs())
    assert cfg.get_base_url == "http://api.local"
    assert cfg.get_api_url == "http://api.local/api"


def test_get_app_config_returns_appconfig_instance(monkeypatch):
    class Fake:
        def __init__(self):
            self._fake = True

    # Replace AppConfig symbol in module and ensure get_app_config returns our Fake
    monkeypatch.setattr(app_config, "AppConfig", Fake)
    inst = app_config.get_app_config()
    assert isinstance(inst, Fake)
    assert getattr(inst, "_fake", False) is True
