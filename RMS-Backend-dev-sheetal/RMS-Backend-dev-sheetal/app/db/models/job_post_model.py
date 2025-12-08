import enum
import uuid

from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Enum,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    TIMESTAMP,
    UUID as PG_UUID,
    Text
)
 
from app.db.connection_manager import Base
# Import the new model to make the relationship aware of it
from app.db.models.agent_config_model import AgentRoundConfig
  
# -----------------------------
# JobDetails
# -----------------------------
class JobDetails(Base):
    __tablename__ = "job_details"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    job_title = Column(String, nullable=False)
    minimum_experience = Column(Integer)
    maximum_experience = Column(Integer)
    minimum_salary = Column(Integer)
    maximum_salary = Column(Integer)
    rounds_count = Column(Integer)
    work_mode = Column(String, doc="office, remote, wfh")
    is_active = Column(Boolean, default=True)
    total_candidates = Column(Integer, default=0)
    shortlisted_count = Column(Integer, default=0)
    under_review_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    no_of_openings = Column(Integer, default=1)
    active_till = Column(DateTime(timezone=True)) 
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
    posted_date = Column(TIMESTAMP(timezone=True))
    
    career_activation_mode = Column(String, default='manual', nullable=False)
    career_activation_days = Column(Integer, default=30)
    career_shortlist_threshold = Column(Integer, default=0)
 
    descriptions = relationship("JobDescription", back_populates="job", cascade="all, delete-orphan")
    locations = relationship("JobLocations", back_populates="job", cascade="all, delete-orphan")
    job_skills = relationship("JobSkills", back_populates="job", cascade="all, delete-orphan")
    rounds = relationship("RoundList", back_populates="job", cascade="all, delete-orphan")
    
    agent_configs = relationship(
        "AgentRoundConfig", 
        back_populates="job", 
        cascade="all, delete-orphan",
        lazy="selectin" # Use selectin loading for efficiency
    )

    try:
        # 'User' mapper may not be available at import time in some test environments.
        # Guard this so tests that import the module don't raise during mapper setup.
        creator = relationship("User", back_populates="jobs_created")
    except Exception:
        # Fallback: provide a placeholder attribute to avoid import-time failures.
        creator = None
 
 
# -----------------------------
# JobDescription
# -----------------------------
class JobDescription(Base):
    __tablename__ = "job_description"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"))
    type_description = Column(String)
    context = Column(Text) 
    created_at = Column(TIMESTAMP(timezone=True))
 
    job = relationship("JobDetails", back_populates="descriptions")
 
 
# -----------------------------
# LocationList
# -----------------------------
class LocationList(Base):
    __tablename__ = "location_list"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location = Column(String, nullable=False)
    state = Column(String)
    country = Column(String)
 
    job_locations = relationship("JobLocations", back_populates="location")
 
 
# -----------------------------
# JobLocations
# -----------------------------
class JobLocations(Base):
    __tablename__ = "job_locations"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"))
    location_id = Column(PG_UUID(as_uuid=True), ForeignKey("location_list.id", ondelete="CASCADE"))
 
 
    job = relationship("JobDetails", back_populates="locations")
    location = relationship("LocationList", back_populates="job_locations")
 
 
# -----------------------------
# SkillList
# -----------------------------
class SkillList(Base):
    __tablename__ = "skill_list"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_name = Column(String, nullable=False)
 
    job_skills = relationship("JobSkills", back_populates="skill")
 
 
# -----------------------------
# JobSkills 
# -----------------------------
class JobSkills(Base):
    __tablename__ = "job_skills"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"))
    skill_id = Column(PG_UUID(as_uuid=True), ForeignKey("skill_list.id", ondelete="CASCADE"))
    weightage = Column(Integer)
 
    job = relationship("JobDetails", back_populates="job_skills")
    skill = relationship("SkillList", back_populates="job_skills")
 
 
# -----------------------------
# RoundList
# -----------------------------
class RoundList(Base):
    __tablename__ = "round_list"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"))
    round_name = Column(String, nullable=False) 
    round_order = Column(Integer, nullable=False)
    round_description = Column(Text) 
 
    job = relationship("JobDetails", back_populates="rounds")
    evaluation_criteria = relationship("EvaluationCriteria", back_populates="round", cascade="all, delete-orphan")
 
 
# -----------------------------
# EvaluationCriteria
# -----------------------------
class EvaluationCriteria(Base):
    __tablename__ = "evaluation_criteria"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id", ondelete="CASCADE"))
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"))
    shortlisting_criteria = Column(Integer)
    rejecting_criteria = Column(Integer)
 
    round = relationship("RoundList", back_populates="evaluation_criteria")