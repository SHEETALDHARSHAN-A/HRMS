# app/services/job_post/get_job_post.py

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.job_post.job_post_reader import JobPostReader

class GetJobPost:
    """Service for fetching individual job posts."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.reader = JobPostReader(db_session)
    
    async def fetch_full_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full job details by ID."""
        job_candidate = self.reader.get_job(job_id=job_id)
        return await job_candidate if hasattr(job_candidate, '__await__') else job_candidate