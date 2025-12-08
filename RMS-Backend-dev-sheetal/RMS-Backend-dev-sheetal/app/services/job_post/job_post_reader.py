# app/services/job_post/job_post_reader.py

"""Service helpers for fetching job post data via repositories."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository.job_post_repository import (
    get_all_job_details,
    get_active_job_details,
    get_job_details_by_id,
    get_jobs_by_user_id,
)
from app.services.job_post.job_post_serializer import (
    serialize_admin_job,
    serialize_job_details,
    serialize_public_job,
)


class JobPostReader:
    """Read-only job post operations built on repository helpers."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = await get_job_details_by_id(db=self._db, job_id=job_id)
        if not job:
            return None
        return serialize_job_details(job)

    async def list_all(self) -> List[Dict[str, Any]]:
        jobs = await get_all_job_details(db=self._db)

        return [serialize_job_details(job) for job in jobs]

    async def list_active(self) -> List[Dict[str, Any]]:
        jobs = await get_active_job_details(db=self._db)
        return [serialize_public_job(job) for job in jobs]

    async def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Optimized query to fetch jobs created only by a specific user."""
        jobs = await get_jobs_by_user_id(db=self._db, user_id=user_id)
        return [serialize_admin_job(job) for job in jobs]








# """Service helpers for fetching job post data via repositories."""
# from __future__ import annotations

# from typing import Any, Dict, List, Optional

# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.repository.job_post_repository import (
#     get_all_job_details,
#     get_active_job_details,
#     get_job_details_by_id,
# )
# from app.services.job_post.job_post_serializer import (
#     serialize_admin_job,
#     serialize_job_details,
#     serialize_public_job,
# )


# class JobPostReader:
#     """Read-only job post operations built on repository helpers."""

#     def __init__(self, db: AsyncSession):
#         self._db = db

#     async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
#         job = await get_job_details_by_id(db=self._db, job_id=job_id)
#         if not job:
#             return None
#         return serialize_job_details(job)

#     async def list_all(self) -> List[Dict[str, Any]]:
#         jobs = await get_all_job_details(db=self._db)
#         return [serialize_admin_job(job) for job in jobs]

#     async def list_active(self) -> List[Dict[str, Any]]:
#         jobs = await get_active_job_details(db=self._db)
#         return [serialize_public_job(job) for job in jobs]
