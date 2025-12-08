# app/services/job_post/job_post_management_service.py

import uuid
import logging

from typing import List
from fastapi import HTTPException, status
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job_post_model import (
    JobDetails,
    JobSkills,
    JobDescription,
    JobLocations,
    RoundList,
    EvaluationCriteria
)
from app.db.repository.job_post_repository import get_job_details_by_id

logger = logging.getLogger(__name__)

# Helper function to safely execute SQL with optional parameters
async def _execute_delete(db: AsyncSession, statement: str, params: dict = None):
    """Executes a text-based DELETE statement with parameter binding."""
    # This function is used primarily for the manual FK cleanup where SQLAlchemy ORM objects aren't available/convenient.
    return await db.execute(text(statement), params)


class JobPostManagementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def hard_delete_job(self, job_id: uuid.UUID) -> dict:
        """
        Permanently deletes a single job and all its associated child records.
        
        This is a destructive, irreversible operation.
        """
        # First, validate the job exists
        job_exists = await get_job_details_by_id(self.db, str(job_id))
        if not job_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job post with ID '{job_id}' not found."
            )

        job_id_str = str(job_id)
        
        # Delete in order of dependency (children first)
        await self.db.execute(delete(EvaluationCriteria).where(EvaluationCriteria.job_id == job_id))
        
        # Remove interview_rounds that reference rounds belonging to this job
        await _execute_delete(
            self.db,
            "DELETE FROM interview_rounds WHERE round_id IN (SELECT id FROM round_list WHERE job_id = :job_id)",
            {"job_id": job_id_str}
        )
        
        await self.db.execute(delete(RoundList).where(RoundList.job_id == job_id))
        await self.db.execute(delete(JobSkills).where(JobSkills.job_id == job_id))
        await self.db.execute(delete(JobDescription).where(JobDescription.job_id == job_id))
        await self.db.execute(delete(JobLocations).where(JobLocations.job_id == job_id))
        
        # 1. Get all profile IDs for this job
        res_profile_ids = await self.db.execute(
            text("SELECT id FROM profiles WHERE job_id = :job_id"),
            {"job_id": job_id_str}
        )
        profile_ids = [row[0] for row in res_profile_ids.fetchall()]
        
        if profile_ids:
            # 2a. FIX: Delete all scheduling_interviews rows referencing these profile IDs
            # This must run BEFORE deleting the profiles.
            params = {f"pid{i}": str(pid) for i, pid in enumerate(profile_ids)}
            placeholders = ", ".join([f":pid{i}" for i in range(len(profile_ids))])
            await _execute_delete(
                self.db,
                f"DELETE FROM scheduling_interviews WHERE profile_id IN ({placeholders})",
                params
            )
            
            # 2b. Delete all curation rows referencing these profile IDs
            await _execute_delete(
                self.db,
                f"DELETE FROM curation WHERE profile_id IN ({placeholders})",
                params
            )

        # Now delete profiles
        res_profiles = await _execute_delete(
            self.db,
            "DELETE FROM profiles WHERE job_id = :job_id",
            {"job_id": job_id_str}
        )
        
        logger.info(f"Removed {getattr(res_profiles, 'rowcount', 'unknown')} profiles referencing job {job_id}")
        
        # Finally, delete the main job post
        await self.db.execute(delete(JobDetails).where(JobDetails.id == job_id))

        # Persist the transaction. get_db() does not commit automatically, so we must commit here.
        try:
            await self.db.commit()
        except Exception:
            # Ensure we rollback on failure to avoid leaving the session in a bad state
            await self.db.rollback()
            logger.exception(f"Failed to commit DB transaction while deleting job {job_id}")
            raise

        logger.info(f"Permanently deleted job with ID: {job_id}")
        return {"job_id": job_id_str, "status": "permanently_deleted"}
            

    async def hard_delete_jobs_batch(self, job_ids: List[uuid.UUID]) -> dict:
        """
        Permanently deletes a batch of jobs and all their associated child records.
        
        This is a destructive, irreversible operation.
        """
        if not job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No job IDs provided for deletion."
            )
        
        job_ids_str = [str(jid) for jid in job_ids]
        
        # Removed the try...except block here as well.

        # Batch delete all children first
        await self.db.execute(delete(EvaluationCriteria).where(EvaluationCriteria.job_id.in_(job_ids)))

        # 1) collect round ids belonging to the jobs
        res = await self.db.execute(select(RoundList.id).where(RoundList.job_id.in_(job_ids)))
        round_ids = [r for r, in res.fetchall()]
        if round_ids:
            params = {f"r{i}": str(rid) for i, rid in enumerate(round_ids)}
            placeholders = ", ".join([f":r{i}" for i in range(len(round_ids))])
            await _execute_delete(self.db, f"DELETE FROM interview_rounds WHERE round_id IN ({placeholders})", params)

        await self.db.execute(delete(RoundList).where(RoundList.job_id.in_(job_ids)))
        await self.db.execute(delete(JobSkills).where(JobSkills.job_id.in_(job_ids)))
        await self.db.execute(delete(JobDescription).where(JobDescription.job_id.in_(job_ids)))
        await self.db.execute(delete(JobLocations).where(JobLocations.job_id.in_(job_ids)))
        
        # 1. Get all profile IDs for the job_ids
        params = {f"jid{i}": str(jid) for i, jid in enumerate(job_ids)}
        placeholders = ", ".join([f":jid{i}" for i in range(len(job_ids))])
        res_profile_ids = await self.db.execute(
            text(f"SELECT id FROM profiles WHERE job_id IN ({placeholders})"),
            params
        )
        profile_ids = [row[0] for row in res_profile_ids.fetchall()]

        # 2a. FIX: Delete all scheduling_interviews rows referencing these profile IDs
        if profile_ids:
            curation_params = {f"pid{i}": str(pid) for i, pid in enumerate(profile_ids)}
            curation_placeholders = ", ".join([f":pid{i}" for i in range(len(profile_ids))])
            await _execute_delete(
                self.db,
                f"DELETE FROM scheduling_interviews WHERE profile_id IN ({curation_placeholders})",
                curation_params
            )
            
        # 2b. Delete from curation first
        if profile_ids:
            curation_params = {f"pid{i}": str(pid) for i, pid in enumerate(profile_ids)}
            curation_placeholders = ", ".join([f":pid{i}" for i in range(len(profile_ids))])
            await _execute_delete(
                self.db,
                f"DELETE FROM curation WHERE profile_id IN ({curation_placeholders})",
                curation_params
            )

        # 3. Now delete from profiles
        await _execute_delete(
            self.db,
            f"DELETE FROM profiles WHERE job_id IN ({placeholders})",
            params
        )

        # 4. Now delete the jobs
        result = await self.db.execute(delete(JobDetails).where(JobDetails.id.in_(job_ids)))
        deleted_count = result.rowcount

        # Persist the transaction. get_db() does not commit automatically, so commit here.
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to commit DB transaction during batch delete")
            raise
        if deleted_count == 0:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching jobs were found or deleted. They may have been deleted already."
            )

        logger.info(f"Permanently deleted {deleted_count} jobs.")
        return {
            "deleted_count": deleted_count,
            "job_ids": job_ids_str,
            "status": "permanently_deleted"
        }