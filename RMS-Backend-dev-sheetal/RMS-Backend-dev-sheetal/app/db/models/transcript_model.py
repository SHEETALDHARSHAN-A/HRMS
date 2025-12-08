import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from datetime import datetime, timezone
from app.db.connection_manager import Base

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys to link the transcript to the context
    profile_id = Column(UUID(as_uuid=True), ForeignKey('profiles.id'), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey('job_details.id'), nullable=False)
    # Store the round_list id (references round_list.id) so transcripts keep the canonical round metadata
    round_id = Column(UUID(as_uuid=True), ForeignKey('round_list.id'), nullable=True)
    
    # Store the LiveKit room name (which is the interview_token)
    room_id = Column(String, index=True)
    
    # Store the conversation as a JSON array
    # [{"speaker": "agent", "speech": "...", "timestamp": "..."}]
    # Use a callable for default to avoid sharing a mutable list across instances
    conversation = Column(JSONB, nullable=False, default=list)
    
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime(timezone=True), nullable=True)
    # Snapshot of the round metadata (name, description) at time of interview
    round_meta = Column(JSONB, nullable=True)

    # Relationships
    profile = relationship("Profile")
    job = relationship("JobDetails")
    round = relationship("RoundList")