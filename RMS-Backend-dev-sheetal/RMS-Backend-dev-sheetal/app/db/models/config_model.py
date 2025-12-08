# app/db/models/config_model.py

import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, String, Text, UniqueConstraint
# Assume Base comes from app.db.connection_manager
from app.db.connection_manager import Base
from datetime import datetime, timezone
from sqlalchemy import TIMESTAMP

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Use a key to identify the template type (e.g., 'interview_invite', 'otp_verification')
    template_key = Column(String, nullable=False, unique=True, index=True)
    subject_template = Column(Text, nullable=False)
    body_template_html = Column(Text, nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('template_key', name='uq_template_key'),
    )