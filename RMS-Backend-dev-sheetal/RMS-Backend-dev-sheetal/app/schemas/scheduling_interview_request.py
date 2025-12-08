# app/schemas/scheduling_interview_request.py

from typing import List
from datetime import date, time
from pydantic import BaseModel, Field

class SchedulingInterviewRequest(BaseModel):
    job_id: str = Field(..., description="UUID of the job post.")
    profile_id: List[str] = Field(..., min_length=1, description="List of UUIDs of candidate profiles to schedule.")
    round_id: str = Field(..., description="UUID of the interview round.")
   
    # We use date and time primitives for cleaner client-side input
    interview_date: date = Field(..., description="Date of the interview (YYYY-MM-DD)")
    interview_time: time = Field(..., description="Time of the interview (HH:MM:SS)")
   
    # Add fields relevant to the scheduling configuration
    interviewer_id: str | None = Field(None, description="Optional UUID of the interviewer/owner.")
    interview_type: str = Field("Agent_interview", description="e.g., 'Agent_interview' / 'In_person'")
    level_of_interview: str = Field("easy", description="e.g., 'easy' / 'medium' / 'hard'")

    email_subject: str | None = Field(None, description="Optional email subject for the interview invite.")
    email_body: str | None = Field(None, description="Optional email body for the interview invite.")
 
    class Config:
        from_attributes = True
