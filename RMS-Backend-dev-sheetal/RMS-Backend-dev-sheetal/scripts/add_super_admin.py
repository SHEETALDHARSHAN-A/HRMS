# scripts/add_super_admin.py

import os
import sys
import uuid
import asyncio

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(backend_dir, ".env"))
except ImportError:
    print("python-dotenv is not installed. Install it using 'pip install python-dotenv'")
    sys.exit(1)

from app.config.app_config import AppConfig
from app.db.models.user_model import User
from app.db.models.job_post_model import JobDetails 
from app.db.connection_manager import Base, engine, AsyncSessionLocal

settings = AppConfig()


SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "athi@mailinator.com")
SUPER_ADMIN_FIRST_NAME = os.getenv("SUPER_ADMIN_FIRST_NAME", "sheetal")
SUPER_ADMIN_LAST_NAME = os.getenv("SUPER_ADMIN_LAST_NAME", "a")
SUPER_ADMIN_TYPE = os.getenv("SUPER_ADMIN_TYPE", "SUPER_ADMIN")
SUPER_ADMIN_PHONE = os.getenv("SUPER_ADMIN_PHONE","7708863679")
# ---------------------------------------------------------------
async def add_or_update_super_admin():
    # Ensure tables are created if this is the very first run
    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if the Super Admin already exists
        result = await session.execute(
            select(User).where(User.email == SUPER_ADMIN_EMAIL)
        )
        existing_user: User = result.scalars().first()

        if existing_user:
            if existing_user.role == SUPER_ADMIN_TYPE:
                print(f"Super Admin with email {SUPER_ADMIN_EMAIL} already exists.")
                if SUPER_ADMIN_PHONE:
                    # Update phone if provided and different
                    if getattr(existing_user, "phone_number", None) != SUPER_ADMIN_PHONE:
                        existing_user.phone_number = SUPER_ADMIN_PHONE
                        await session.commit()
                        print(f"Updated phone number for {SUPER_ADMIN_EMAIL}.")
            else:
                print(f"User found with email {SUPER_ADMIN_EMAIL}, upgrading role to SUPER_ADMIN.")
                existing_user.role = SUPER_ADMIN_TYPE
                await session.commit()
        else:
            # Create the new Super Admin
            new_user = User(
                user_id=uuid.uuid4(), 
                first_name=SUPER_ADMIN_FIRST_NAME,
                last_name=SUPER_ADMIN_LAST_NAME,
                email=SUPER_ADMIN_EMAIL,
                phone_number=SUPER_ADMIN_PHONE,
                role=SUPER_ADMIN_TYPE
            )
            session.add(new_user)
            await session.commit()
            print(f"Successfully created initial SUPER_ADMIN: {SUPER_ADMIN_EMAIL}")
            if SUPER_ADMIN_PHONE:
                print(f"Phone number set: {SUPER_ADMIN_PHONE}")

if __name__ == "__main__":
    try:
        print("Starting super admin creation process...")
        asyncio.run(add_or_update_super_admin())
        print("Script completed successfully!")
    except Exception as e:
        print(f"Error running script: {str(e)}")
        raise
