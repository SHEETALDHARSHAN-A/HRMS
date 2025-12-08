import os
import redis
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file
load_dotenv(override=True)

class AppConfig(BaseSettings): 
    # --- Core Config ---
    environment: str
    port: int = 8000 

    # --- Redis Config (Worker Critical) ---
    redis_host: str 
    redis_port: int 
    redis_db: int 

    # --- OpenAI Config (Worker Critical) ---
    openai_api_key: str 
    openai_model: str 
    temperature: float
    openai_cache: bool
    
    # --- PostgreSQL Config (Worker Critical) ---
    db_name: str 
    db_user: str 
    db_password: str 
    db_host: str 
    db_port: int
    db_pool_size: int
    db_max_over_flow: int
    
    # --- Worker Config (Worker Critical) ---
    worker_poll_interval: int
    worker_lock_timeout: int
    poppler_path: str 
    file_path: str
    # The Redis list name the worker listens on for incoming tasks
    job_queue: str = "resume_queue"
    status_channel : str
    
    # --- Worker Set Config ---
    worker_set: str = Field(default="", description="Comma-separated list of worker configurations.")

    # --- Worker Heartbeat Config ---
    worker_heartbeat: str = Field(default="30", description="Interval in seconds for worker heartbeat checks.")

    # --- NON-WORKER / OPTIONAL FIELDS (Set to Optional to allow Worker to load) ---
    
    # Auth & Security Fields (API/Auth specific)
    APP_BASE_URL: Optional[str] = None
    FRONTEND_BASE_URL: Optional[str] = None
    ACCESS_REFRESH_TOKEN_EXPIRE_HOURS: Optional[int] = None
    
    OTP_EXPIRE_SECONDS: Optional[int] = None
    SAMESITE: Optional[str] = None
    SECURE: Optional[bool] = None
    SECRET_KEY: Optional[str] = None
    ALGORITHM: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = None
    
    ALLOW_ORIGINS: Optional[List[str]] = None
    ALLOW_DOMAINS: Optional[List[str]] = None
    
    # Email/Invitation Fields (API/Auth specific)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    REPORT_MAIL: Optional[str] = None
    LINK_EXPIRATION: Optional[int] = None
    INVITE_EXPIRE_MINUTES: Optional[int] = None
    INVITE_EXPIRE_SECONDS: Optional[int] = None

    # Other Config
    DEFAULT_TENANT_ID: Optional[str] = None

    # --- Pydantic Settings ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow" 
    )

def get_app_config() -> AppConfig:
    """Singleton function to load and return the application configuration."""
    return AppConfig()
