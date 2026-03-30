from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class InterviewCompletionRequest(BaseModel):
    token: str = Field(..., min_length=6, description="Interview token (LiveKit room id)")
    email: EmailStr
    session_id: Optional[str] = Field(default=None, description="Optional transcript session UUID")
    final_notes: Optional[str] = Field(default=None, max_length=2000)
