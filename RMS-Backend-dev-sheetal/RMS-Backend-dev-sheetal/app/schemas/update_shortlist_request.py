# app/schemas/update_shortlist_request.py

from typing import Optional
from pydantic import BaseModel, Field

class UpdateShortlistRequest(BaseModel):
    new_result: str = Field(..., description="New status for the candidate ('shortlist', 'reject', or 'under_review').")
    reason: str = Field(None, description="Reason for the status update.")