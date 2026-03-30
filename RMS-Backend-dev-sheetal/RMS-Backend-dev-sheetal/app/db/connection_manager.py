# app/db/connection_manager.py

from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.engine import URL

from app.config.app_config import AppConfig
import os

settings = AppConfig()

database_url = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=int(settings.db_port),
    database=settings.db_name,
)

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    pool_size=int(settings.db_pool_size),
    max_overflow=int(settings.db_max_over_flow),
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

if os.getenv("TESTING"):
    class _DummyBase:
        pass
    Base = _DummyBase
else:
    Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)