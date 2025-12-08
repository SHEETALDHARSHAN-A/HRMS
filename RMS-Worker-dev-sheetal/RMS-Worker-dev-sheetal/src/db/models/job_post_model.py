# src/db/models/job_post_model.py
 
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

from src.db.models.user_model import User 
from src.db.connection_manager import Base

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
    rounds_count = Column(Integer)
    work_mode = Column(String, doc="office, remote, wfh")
    is_active = Column(Boolean, default=True)
    role_fit = Column(Integer)
    location_fit = Column(Integer)
    potential_fit = Column(Integer)
 
    interview_type = Column(String)
    total_candidates = Column(Integer, default=0)
    shortlisted_count = Column(Integer, default=0)
    under_review_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    no_of_openings = Column(Integer, default=1)
    active_till = Column(DateTime(timezone=True))
    is_agent_interview = Column(Boolean, default=False)
 
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
    posted_date = Column(TIMESTAMP(timezone=True))
   
 
    descriptions = relationship("JobDescription", back_populates="job")
    locations = relationship("JobLocations", back_populates="job")
    job_skills = relationship("JobSkills", back_populates="job")
    rounds = relationship("RoundList", back_populates="job")
 
 
# -----------------------------
# JobDescription
# -----------------------------
class JobDescription(Base):
    __tablename__ = "job_description"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"))
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
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"))
    location_id = Column(PG_UUID(as_uuid=True), ForeignKey("location_list.id"))
 
 
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
# JobSkills (Note the plural name)
# -----------------------------
class JobSkills(Base):
    __tablename__ = "job_skills"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"))
    skill_id = Column(PG_UUID(as_uuid=True), ForeignKey("skill_list.id"))
    weightage = Column(Integer)
 
    job = relationship("JobDetails", back_populates="job_skills")
    skill = relationship("SkillList", back_populates="job_skills")
 
 
# -----------------------------
# RoundList
# -----------------------------
class RoundList(Base):
    __tablename__ = "round_list"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"))
    round_name = Column(String, nullable=False)
    round_order = Column(Integer, nullable=False)
    round_description = Column(Text)
 
    job = relationship("JobDetails", back_populates="rounds")
    evaluation_criteria = relationship("EvaluationCriteria", back_populates="round")
 
 
# -----------------------------
# EvaluationCriteria
# -----------------------------
class EvaluationCriteria(Base):
    __tablename__ = "evaluation_criteria"
 
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id"))
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id"))
    shortlisting_criteria = Column(Integer)
    rejecting_criteria = Column(Integer)
 
    round = relationship("RoundList", back_populates="evaluation_criteria")