#src/db/models/shortlist_model.py

import uuid

from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, Integer, Text, String, TIMESTAMP, ForeignKey

from app.db.connection_manager import Base

class Shortlist(Base):
    __tablename__ = "shortlist"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"), nullable=False)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    curation_id = Column(PG_UUID(as_uuid=True), ForeignKey("curation.id", ondelete="CASCADE"), nullable=False)

    overall_score = Column(Integer, nullable=True)
    score_explanation = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    result = Column(String(50), nullable=False, default="under_review")

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("JobDetails", backref="shortlists")
    profile = relationship("Profile", backref="shortlists")
    curation = relationship("Curation", back_populates="shortlist", uselist=False)
