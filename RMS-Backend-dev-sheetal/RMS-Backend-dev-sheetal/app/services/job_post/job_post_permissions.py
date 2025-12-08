# app/services/job_post_job_post_permissions.py

"""Job post permission and access control utilities."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.db.models.job_post_model import JobDetails

class JobPostPermissions:
    """Handle job post access control and permissions."""
    
    @staticmethod
    def can_edit_job(job: JobDetails, current_user: Optional[Dict[str, Any]]) -> bool:
        """Check if current user can edit the given job post."""
        if not current_user:
            return False
            
        user_id = current_user.get("user_id") or current_user.get("sub")
        user_role = current_user.get("role") or current_user.get("user_role", "").upper()
        
        if user_role == "SUPER_ADMIN":
            return True
            
        if user_id and str(job.user_id) == str(user_id):
            return True
            
        return False
        
    @staticmethod
    def can_view_job(job: JobDetails, current_user: Optional[Dict[str, Any]]) -> bool:
        """Check if current user can view the given job post."""
        # All authenticated users can view jobs
        # Public jobs (active) can be viewed by anyone
        return True
        
    @staticmethod
    def filter_jobs_by_ownership(
        jobs: List[Dict[str, Any]], 
        current_user: Optional[Dict[str, Any]],
        show_own_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Filter jobs based on ownership and set permissions."""
        if not current_user:
            return jobs
            
        user_id = current_user.get("user_id") or current_user.get("sub")
        user_role = current_user.get("role") or current_user.get("user_role", "").upper()
        
        filtered_jobs = []
        
        for job in jobs:
            job_user_id = job.get("user_id") or job.get("created_by_user_id") or job.get("author_id")
            is_own_job = user_id and str(job_user_id) == str(user_id)
            
            if show_own_only and not is_own_job:
                continue
                
            # Set permission flags
            job["can_edit"] = (
                user_role == "SUPER_ADMIN" or 
                is_own_job
            )
            job["is_own_job"] = is_own_job
            
            # Add creator info for display
            if not is_own_job and job_user_id:
                job["created_by_other"] = True
                # You might want to fetch creator name from user service here
                job["creator_name"] = f"User {job_user_id[:8]}"  # Placeholder
            else:
                job["created_by_other"] = False
                job["creator_name"] = "You"
                
            filtered_jobs.append(job)
            
        return filtered_jobs