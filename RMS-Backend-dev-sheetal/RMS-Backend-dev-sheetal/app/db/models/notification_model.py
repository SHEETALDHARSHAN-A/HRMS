# app/db/models/notification_model.py

import uuid

from enum import Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey

from app.db.connection_manager import Base

class NotificationType(Enum):
    INVITATION_ACCEPTED = "INVITATION_ACCEPTED"
    INVITATION_EXPIRED = "INVITATION_EXPIRED"
    USER_UPDATED = "USER_UPDATED"
    SYSTEM_ALERT = "SYSTEM_ALERT"

class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4
    )
    
    # Who should receive this notification
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    
    # Notification details
    type = Column(String(50), nullable=False)  # NotificationType enum values
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Optional reference to related entities
    related_invitation_id = Column(UUID(as_uuid=True), ForeignKey("invitations.invitation_id"), nullable=True)
    related_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    recipient = relationship("User", foreign_keys=[user_id], backref="notifications")
    related_invitation = relationship("Invitation", foreign_keys=[related_invitation_id])
    related_user = relationship("User", foreign_keys=[related_user_id])