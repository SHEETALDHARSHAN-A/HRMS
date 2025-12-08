# app/db/models/invitation_model.py

import uuid

from enum import Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, Text, ForeignKey

from app.db.connection_manager import Base

class InvitationStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED" 
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

class Invitation(Base):
    __tablename__ = "invitations"
    
    invitation_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4
    )
    
    # Who sent the invitation
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    
    # Invitation details
    invited_email = Column(String(255), nullable=False, index=True)
    invited_first_name = Column(String(100), nullable=False)
    invited_last_name = Column(String(100), nullable=True)
    invited_phone_number = Column(String(50), nullable=True)
    invited_role = Column(String(20), nullable=False)  # SUPER_ADMIN, ADMIN, HR
    
    # Status tracking
    status = Column(String(20), nullable=False, default=InvitationStatus.PENDING.value)
    
    # If accepted, link to the created user
    accepted_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    
    # Token for invitation link (stored hashed for security)
    invitation_token = Column(String(255), nullable=False, unique=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    inviter = relationship("User", foreign_keys=[invited_by], backref="sent_invitations")
    accepted_user = relationship("User", foreign_keys=[accepted_user_id], backref="received_invitations")