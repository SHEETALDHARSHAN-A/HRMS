import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from app.db.connection_manager import Base

class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("job_details.id", ondelete="CASCADE"), nullable=False, index=True)
    round_list_id = Column(PG_UUID(as_uuid=True), ForeignKey("round_list.id", ondelete="CASCADE"), nullable=False, index=True)

    interview_token = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, index=True)

    question_payload = Column(JSONB, nullable=False, default=dict)
    challenge_type = Column(String, nullable=False, default="coding")
    language = Column(String, nullable=False, default="python")
    code = Column(Text, nullable=False)
    submitted_answers = Column(JSONB, nullable=True)
    test_case_results = Column(JSONB, nullable=True)

    status = Column(String, nullable=False, default="evaluated")
    evaluation_source = Column(String, nullable=True)
    max_score = Column(Integer, nullable=True)
    passed = Column(Boolean, nullable=True)
    ai_score = Column(Integer, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    ai_breakdown = Column(JSONB, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )