import os
import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

# --- Configuration (using Pydantic Settings) ---

# Define the settings class
class Settings(BaseSettings):
    # LiveKit (Required for the API to run)
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    
    # AI Services (Required for Agent Plugins)
    OPENAI_API_KEY: str
    CARTESIA_API_KEY: str
    DEEPGRAM_API_KEY: str
    ELEVEN_LABS_API_KEY: str
    
    # Langfuse (Observability)
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_HOST: str
    
    # --- MODIFIED: PostgreSQL Settings ---
    # These should point to your RMS-Backend database
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="admin")
    POSTGRES_HOST: str = Field(default="100.108.207.86")
    POSTGRES_DB: str = Field(default="ATS")
    POSTGRES_PORT: int = Field(default=5433)
    
    # Other settings
    LIVEKIT_INFERENCE_TIMEOUT: int = Field(default=120)

    # CRITICAL: Configure Pydantic to read environment variables and look for .env file
    model_config = SettingsConfigDict(
        env_file=find_dotenv(usecwd=True),
        env_file_encoding='utf-8',
        case_sensitive=True,
    )

# Instantiate the settings object
try:
    settings = Settings()
except Exception as e:
    print(f"FATAL CONFIG ERROR: Pydantic failed to load settings. Ensure all required keys are in .env. Error: {e}")
    raise e

# --- CRITICAL FIX: Set OS environment variables for livekit-agents CLI ---
os.environ['LIVEKIT_API_KEY'] = settings.LIVEKIT_API_KEY
os.environ['LIVEKIT_API_SECRET'] = settings.LIVEKIT_API_SECRET
os.environ['LIVEKIT_URL'] = settings.LIVEKIT_URL 
os.environ['LIVEKIT_INFERENCE_TIMEOUT'] = str(settings.LIVEKIT_INFERENCE_TIMEOUT)

# --- Logging Setup ---
logger = logging.getLogger("professional-interview-agent")
logger.setLevel(logging.INFO)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

# --- NEW: PostgreSQL Connection Setup ---
try:
    SQLALCHEMY_DATABASE_URL = URL.create(
        drivername="postgresql+psycopg2",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )
    
    # The agent will use this engine to create sessions
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # SessionLocal will be used by the data fetcher
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("PostgreSQL connection engine created successfully.")
    
except Exception as e:
    logger.error(f"FATAL DB ERROR: Failed to create PostgreSQL engine. Error: {e}")
    engine = None
    SessionLocal = None
    raise e