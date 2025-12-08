#src/db/models/resume_model.py

import uuid

from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Enum

from app.db.connection_manager import Base

# -----------------------------
# Profiles
# -----------------------------
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"), nullable=False)

    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_hash = Column(Text, nullable=True)
    resume_link = Column(String, nullable=True)
    extracted_content = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Relationships
    job = relationship("JobDetails", backref="profiles")
    interview_rounds = relationship("InterviewRounds", back_populates="profile")

# -----------------------------
# InterviewRounds
# -----------------------------
class InterviewRounds(Base):
    __tablename__ = "interview_rounds"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"), nullable=False)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    round_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id"), nullable=False)
    status = Column(String, nullable=True)

    # Relationships
    job = relationship("JobDetails", backref="interview_rounds")
    profile = relationship("Profile", back_populates="interview_rounds")
    round = relationship("RoundList", backref="interview_rounds")
