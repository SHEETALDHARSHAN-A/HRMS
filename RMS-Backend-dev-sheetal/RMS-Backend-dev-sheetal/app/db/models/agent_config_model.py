import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.connection_manager import Base

class AgentRoundConfig(Base):
    """
    Stores the specific AI agent configuration for a single interview
    round of a specific job.
    """
    __tablename__ = "round_config"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # This is the FK to the 'round_list' table, which defines the
    # round (e.g., "Technical Screen 1", "System Design").
    round_list_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id", ondelete="CASCADE"), nullable=True, index=True)

    # Denormalized name for easier debugging/display.
    round_name = Column(String, nullable=False, default="Configured Round")
    
    # --- Configuration Fields ---
    # These match the frontend state in AgentHubPage.tsx
    
    # The main prompt/objective for the agent
    round_focus = Column(Text) 
    
    # Persona (e.g., 'alex', 'dr-evan', 'sam')
    persona = Column(String, default='alex', nullable=True)
    
    # List of skills to probe
    key_skills = Column(JSONB, default=list) # Stores string[]
    # List of mandatory questions
    custom_questions = Column(JSONB, default=list) # Stores string[]
    # List of topics to avoid
    forbidden_topics = Column(JSONB, default=list) # Stores string[]
    # --- Interview mode fields ---
    interview_mode = Column(String, default='agent')
    # For agent rounds: interview duration in minutes (min and max)
    interview_time_min = Column(Integer, nullable=True)
    interview_time_max = Column(Integer, nullable=True)

    # For in-person rounds: the interviewer user id (references users.user_id)
    interviewer_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    # Coding challenge controls (MVP): supports AI-generated or admin-provided questions
    coding_enabled = Column(Boolean, default=False, nullable=False)
    coding_question_mode = Column(String, default='ai', nullable=False)
    coding_difficulty = Column(String, default='medium', nullable=True)
    coding_languages = Column(JSONB, default=list, nullable=True)
    provided_coding_question = Column(Text, nullable=True)
    coding_test_case_mode = Column(String, default='ai', nullable=False)
    coding_test_cases = Column(JSONB, default=list, nullable=True)
    coding_starter_code = Column(JSONB, default=dict, nullable=True)

    # MCQ challenge controls
    mcq_enabled = Column(Boolean, default=False, nullable=False)
    mcq_question_mode = Column(String, default='ai', nullable=False)
    mcq_difficulty = Column(String, default='medium', nullable=True)
    mcq_questions = Column(JSONB, default=list, nullable=True)
    mcq_passing_score = Column(Integer, default=60, nullable=True)
    # Optional score distribution for this round's scoring (e.g., {
    #   "shortlisting": 60, "rejecting": 40 }
    score_distribution = Column(JSONB, default=dict, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # --- Relationships ---
    job = relationship("JobDetails", back_populates="agent_configs")
    
    # Link to the round definition in round_list
    round_definition = relationship("RoundList")