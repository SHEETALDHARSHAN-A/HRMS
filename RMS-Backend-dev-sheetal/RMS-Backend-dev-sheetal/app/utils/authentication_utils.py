# app/utils/authentication_utils.py

import random
import redis.asyncio as redis 

from uuid import uuid4
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError

from app.config.app_config import AppConfig
from app.db.redis_manager import get_redis_client, JWT_BLOCKLIST_KEY 

settings = AppConfig()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
ACCESS_REFRESH_TOKEN_EXPIRE_HOURS = settings.access_refresh_token_expire_hours

def create_access_token(user_id: str, role: str, first_name: str | None = None, last_name: str | None = None) -> str:
    """
    Creates an access token including a unique JTI for revocation.
    
    Args:
        user_id: User's unique identifier
        role: User's role (SUPER_ADMIN, ADMIN, HR, CANDIDATE)
        first_name: User's first name (optional)
        last_name: User's last name (optional)
    
    Returns:
        JWT token string
    """
    jti = str(uuid4()) 
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": user_id, "role": role, "exp": expire, "jti": jti}
    if first_name:
        to_encode["fn"] = first_name
    if last_name:
        to_encode["ln"] = last_name
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str, role: str) -> str:
    """
    Creates a refresh token including a unique JTI for revocation.
    
    Args:
        user_id: User's unique identifier
        role: User's role (SUPER_ADMIN, ADMIN, HR, CANDIDATE)
    
    Returns:
        JWT token string
    """
    jti = str(uuid4())
    expire = datetime.utcnow() + timedelta(hours=ACCESS_REFRESH_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": user_id, "role": role, "exp": expire, "jti": jti}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_otp_code(length: int = 6) -> str:
    """Generate an OTP code of given length (numeric).

    The length parameter is supported to avoid unused-parameter warnings and
    to allow future callers to request different lengths. Current callers
    use the default length.
    """
    # Clamp and validate length
    try:
        n = max(4, min(int(length), 12))
    except Exception:
        n = 6

    low = 10 ** (n - 1)
    high = (10 ** n) - 1
    return str(random.randint(low, high))

def get_jti_from_token(token: str) -> str | None:
    """Decodes a JWT (ignoring expiry) and returns the JTI claim."""
    try:
        # We only need the payload data (JTI) for tracking/revocation, not active authentication.
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM], 
            options={"verify_signature": True, "verify_exp": False} # Allow expired tokens to be decoded
        )
        return payload.get("jti")
    except (JWTError, ExpiredSignatureError):
        return None

async def is_jti_revoked(jti: str, cache: redis.Redis) -> bool:
    """Checks if the JWT ID (JTI) exists in the blocklist (Redis).

    This function is defensive: if Redis is unavailable or an error occurs while
    checking the blocklist, we treat the token as NOT revoked (fail-open) but
    log the underlying exception. This prevents transient Redis issues from
    causing 5xx errors in the middleware while allowing operators to notice and
    fix Redis availability.
    """
    if cache is None:
        return False
    try:
        return await cache.exists(JWT_BLOCKLIST_KEY + jti)
    except Exception as e:
        # Log and fail-open (return False) to avoid middleware crashing the request.
        try:
            import logging
            logging.getLogger(__name__).exception(f"Redis error while checking JTI revocation: {e}")
        except Exception:
            pass
        return False

async def add_jti_to_blocklist(jti: str, cache: redis.Redis, max_age_seconds: int):
    """Adds the JWT ID (JTI) to the blocklist with the token's remaining lifespan."""
    await cache.set(JWT_BLOCKLIST_KEY + jti, "", ex=max_age_seconds)

# Renaming for external usage, but keeping the original internal name to avoid mass renaming in other files
add_token_to_blocklist = add_jti_to_blocklist
is_token_revoked = is_jti_revoked
def generate_token() -> str:
    return str(uuid4())