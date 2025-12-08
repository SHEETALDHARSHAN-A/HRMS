# RMS-Backend-dev-sheetal/app/db/models/user_model.py

import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.connection_manager import Base
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    __tablename__ = "users"
    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # 💡 NEW FIELD
    phone_number = Column(String(50), nullable=True) # Added phone number

    user_type = Column(String(20), nullable=False, default="CANDIDATE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # (Relationships remain the same)
    # jobs_created = relationship(
    #     "JobDetails", 
    #     back_populates="creator",
    # )