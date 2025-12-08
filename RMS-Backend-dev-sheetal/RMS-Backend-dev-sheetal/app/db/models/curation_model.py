#src/db/models/curation_model.py

import uuid
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.db.connection_manager import Base

class Curation(Base):
    __tablename__ = "curation"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"), nullable=False)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)

    potential_score = Column(Integer)
    location_score = Column(Integer)
    role_fit_score = Column(Integer)
    skill_score = Column(Integer)
    skill_score_explanation = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Relationships
    job = relationship("JobDetails", backref="curations")
    profile = relationship("Profile", backref="curations")
    shortlist = relationship("Shortlist", back_populates="curation", uselist=False)
