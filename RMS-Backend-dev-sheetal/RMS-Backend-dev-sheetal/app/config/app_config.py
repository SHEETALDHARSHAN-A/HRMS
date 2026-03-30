# app/config/app_config.py

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    # Core Config
    environment: str = "development"
    port: int = 8000
    
    
    # URL Configuration
    app_base_url: str  # Backend API URL
    frontend_url: str  # Frontend Application URL
    frontend_base_url: str  # Alias for frontend_url for backward compatibility
    api_prefix: str = "/api"  # API URL prefix
    
   
    
    @property
    def get_frontend_url(self) -> str:
        """Get the frontend URL, preferring frontend_url over frontend_base_url"""
        return self.frontend_url or self.frontend_base_url
        
    @property
    def get_api_url(self) -> str:
        """Get the backend API URL with prefix"""
        return f"{self.app_base_url}{self.api_prefix}"
        
    @property
    def get_base_url(self) -> str:
        """Get the backend URL without API prefix"""
        return self.app_base_url
    
    # Redis Config
    redis_host: str 
    redis_port: str 
    redis_db: str 

    # AI Provider Config (Groq-first with legacy OpenAI fallback)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openai_api_key: str = ""
    openai_model: str = ""
    temperature: float = 0.2
    openai_cache: bool = False

    @property
    def effective_groq_api_key(self) -> str:
        key = (self.groq_api_key or "").strip()
        if key:
            return key

        legacy_key = (self.openai_api_key or "").strip()
        return legacy_key if legacy_key.startswith("gsk_") else ""

    @property
    def effective_groq_model(self) -> str:
        configured = (self.groq_model or "").strip()
        if configured:
            return configured

        legacy_model = (self.openai_model or "").strip()
        return legacy_model or "llama-3.3-70b-versatile"
    
    # LiveKit Server Config (optional for local/dev)
    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    
    # PostgreSQL Config
    db_name: str 
    db_user: str 
    db_password: str 
    db_host: str 
    db_port: str
    db_pool_size : str
    db_max_over_flow: str
    
    
    # Auth & Security Config
    otp_expire_seconds: int
    smtp_server: str 
    smtp_port: int 
    smtp_username: str
    smtp_password: str
    
    samesite: str
    secure: bool
    allow_origins: List[str] 
    allow_domains: List[str] 
    
    secret_key: str 
    algorithm: str 
    access_token_expire_minutes: int 
    access_refresh_token_expire_hours: int

    # NEW FIELD FOR INVITATION LINK
    app_base_url: str 
    frontend_base_url: str
    invite_expire_minutes: int
    invite_expire_seconds: int

    # Remember Me Config
    remember_me_expire_days: int

    # File Upload Config
    max_file_size_pdf: int = 5 * 1024 * 1024  # 5 MB
    max_file_size_docx: int = 5 * 1024 * 1024  # 5 MB
    max_pdf_pages: int = 10

    # Other Config
    report_mail: str
    default_tenant_id: str
    link_expiration: int
    email_require_templates: bool = False
    # Internal service token used by internal workers to call protected endpoints
    internal_service_token: str | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

def get_app_config() -> AppConfig:
    return AppConfig()