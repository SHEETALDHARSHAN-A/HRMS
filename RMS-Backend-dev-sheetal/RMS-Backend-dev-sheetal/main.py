# main.py

import asyncio
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import v1_router
from app.config.app_config import AppConfig
from app.db.redis_manager import RedisManager
from app.db.connection_manager import init_db
from app.db.connection_manager import AsyncSessionLocal
from app.authentication.jwt_middleware import JWTMiddleware
 
async def lifespan(app: FastAPI):
    """
    Initializes database connections (PostgreSQL) and Redis pool on startup.
    This ensures resources are ready before the server starts accepting requests.
    """
    await init_db()
    await RedisManager.init_pool()
    yield
 
origins = [
    "http://localhost:5173",  
]
 
app = FastAPI(lifespan=lifespan, root_path="/api")
config = AppConfig()
 
app.state.jwt_secret_key = config.secret_key
app.state.jwt_algorithm = config.algorithm
 
app.add_middleware(JWTMiddleware)

# --- CORS Middleware ---
# Register CORS after JWT middleware so CORS headers are included
# even when JWT middleware returns early (for example 401/403 responses).
app.add_middleware(
    CORSMiddleware,
    # Allow origins should be strictly configured in a production .env file
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True, # Critical for cookie-based authentication
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# --- Router Inclusion ---
app.include_router(v1_router, prefix="/v1")
 
if __name__ == "__main__":
    try:
        port = config.port
    except Exception:
        port = 8000
       
    # 'reload=True' is only for development
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
 
    profiles = relationship("Profile", back_populates="job", cascade="all, delete-orphan")
 