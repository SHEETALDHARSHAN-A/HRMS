# app/schemas/job_request.py

import uuid

from typing import List
from pydantic import BaseModel, Field

class BatchDeleteJobsRequest(BaseModel):
    """
    Schema for batch-deleting job posts.
    """
    job_ids: List[uuid.UUID] = Field(..., description="A list of job UUIDs to be permanently deleted.", min_length=1)

    class Config:
        from_attributes = True