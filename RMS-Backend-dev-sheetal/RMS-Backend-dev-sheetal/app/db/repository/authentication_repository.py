# app/db/models/authentication_repository.py

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_model import User
from app.db.repository.user_repository import get_user_by_email, create_user

async def check_user_existence(db: AsyncSession, email: str) -> Optional[User]:
    """Checks if a user already exists in the PostgreSQL database."""
    return await get_user_by_email(db, email)

async def create_user_from_cache(db: AsyncSession, user_details: Dict[str, Any]) -> User:
    """Creates a new user in PostgreSQL using data retrieved from Redis cache."""
    role = user_details.get("role", "CANDIDATE")  
    
    new_user = User(
        first_name=user_details.get("first_name"),
        last_name=user_details.get("last_name"),
        email=user_details.get("email"),
        phone_number=user_details.get("phone_number"),
        role=role
    )
    return await create_user(db, new_user)