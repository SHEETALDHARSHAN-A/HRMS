# app/db/repository/profile_repository.py

from sqlalchemy import select, func
from app.db.models.resume_model import Profile

class ProfileRepository:
    def __init__(self, db):
        self.db = db

    async def count_by_status(self, job_id: str, status: str = None) -> int:
        # If status is 'applied' or None, count all profiles for the job
        if status in (None, "applied"):
            stmt = select(func.count()).select_from(Profile).where(Profile.job_id == job_id)
        else:
            # For other statuses, you may need to join with InterviewRounds or Shortlist
            from app.db.models.resume_model import InterviewRounds
            stmt = select(func.count()).select_from(InterviewRounds).where(
                (InterviewRounds.job_id == job_id) & (InterviewRounds.status == status)
            )
        res = await self.db.execute(stmt)
        return res.scalar() or 0
