import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.db.connection_manager import Base 
class Scheduling(Base):
    __tablename__ = "scheduling_interviews" 
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey('profiles.id'), 
        primary_key=True
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey('job_details.id'),
        primary_key=True 
    )
    round_id = Column(
        UUID(as_uuid=True),
        ForeignKey('interview_rounds.id'),
        primary_key=True 
    )
 
    interview_token = Column(UUID, unique=True, nullable=False) 
    interviewer_id = Column(UUID(as_uuid=True),nullable=True)
    scheduled_datetime = Column(DateTime(timezone=True), nullable=False)
    interview_duration = Column(Integer, nullable=False, default=60)
    status = Column(String, nullable=False, default="scheduled") 
    rescheduled_count = Column(Integer, nullable=False, default=0)
    email_sent = Column(Boolean, nullable=False, default=False)
    phone_number = Column(String(20), nullable=True)
    interview_type = Column(Text, nullable=False, default="Agent_interview") 
    level_of_interview = Column(Text, nullable=False, default="easy") 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    expired_at = Column(DateTime(timezone=True), nullable=True) # Interview token/link expiration
 
   
