# app/db/repository/config_repository.py

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import select, update, insert
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
# Import the new model
from app.db.models.config_model import EmailTemplate 

logger = logging.getLogger(__name__)

class ConfigRepository:

    @staticmethod
    async def get_template_by_key(db: AsyncSession, template_key: str) -> Optional[EmailTemplate]:
        """Fetches an email template by its unique key."""
        try:
            # First try exact match
            stmt = select(EmailTemplate).where(EmailTemplate.template_key == template_key)
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                return record

            # Fallback: case-insensitive match (helps when UI/backend disagree on casing)
            stmt = select(EmailTemplate).where(func.lower(EmailTemplate.template_key) == template_key.lower())
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                return record

            # Final fallback: try normalized variants (replace '-' with '_')
            alt_key = template_key.replace('-', '_')
            if alt_key != template_key:
                stmt = select(EmailTemplate).where(func.lower(EmailTemplate.template_key) == alt_key.lower())
                result = await db.execute(stmt)
                return result.scalar_one_or_none()

            return None
        except Exception as e:
            logger.error(f"[ConfigRepo] get_template_by_key failed: {e}")
            return None
        

    @staticmethod
    async def save_or_update_email_template(
        db: AsyncSession,
        template_key: str,
        subject_template: str,
        body_template_html: str
    ) -> EmailTemplate:
        """Creates a new template or updates an existing one (upsert logic)."""
        timestamp = datetime.now(timezone.utc)
        
        # 1. Check if template exists
        existing_template = await ConfigRepository.get_template_by_key(db, template_key)

        update_data = {
            "subject_template": subject_template,
            "body_template_html": body_template_html,
            "updated_at": timestamp
        }

        if existing_template:
            # 2. Update existing template
            await db.execute(
                update(EmailTemplate)
                .where(EmailTemplate.template_key == template_key)
                .values(**update_data)
            )
            await db.commit()
            
            # Fetch the updated template
            return await ConfigRepository.get_template_by_key(db, template_key)
        else:
            # 3. Insert new template
            insert_data = {
                "template_key": template_key,
                "created_at": timestamp,
                **update_data
            }
            # Use returning() to get the inserted object in a single trip
            stmt = insert(EmailTemplate).values(**insert_data).returning(EmailTemplate)
            result = await db.execute(stmt)
            await db.commit()
            return result.scalar_one()