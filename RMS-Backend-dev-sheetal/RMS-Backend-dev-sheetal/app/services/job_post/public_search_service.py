# app/services/job_post/publisc_search_service.py

import logging

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job_post_model import JobDetails 
from app.db.repository.job_post_repository import (
    search_active_job_details,
    get_search_autocomplete_suggestions
)
from app.services.job_post.job_post_serializer import JobPostSerializer

logger = logging.getLogger(__name__)

class PublicSearchService:
    """
    Service for handling public-facing job searches, including
    ranked results and autocomplete suggestions.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_suggestions(self) -> Dict[str, Any]:
        """
        Fetches autocomplete suggestions for skills and locations.
        """
        try:
            return await get_search_autocomplete_suggestions(db=self.db_session)
        except Exception as e:
            logger.error(f"[PublicSearchService] Failed to get suggestions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch search suggestions."
            )

    async def search_jobs(
        self,
        search_role: Optional[str],
        search_skills: List[str],
        search_locations: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Fetches and ranks active job posts based on search criteria.
        Returns a formatted list suitable for the public career page.
        """
        
        # 1. Call the repository to get ranked ORM objects and their scores
        job_orms_with_scores = await search_active_job_details(
            db=self.db_session,
            search_role=search_role,
            search_skills=search_skills,
            search_locations=search_locations
        )
        
        if not job_orms_with_scores:
            return []

        # 2. Format the results
        formatted_jobs = []
        for job_orm, score in job_orms_with_scores:
            # We use the existing serializer to convert the ORM object to a dict
            # This ensures consistent data structure with other job endpoints
            job_data = JobPostSerializer.format_job_details_orm(job_orm)
            
            # Add the score to our response
            job_data["score"] = score
            
            # We can also add a "short_description" for the card view
            # Let's find the first "Job Overview" or default
            short_desc = "View details to learn more about this role."
            if job_orm.descriptions:
                for desc in job_orm.descriptions:
                    if desc.type_description.lower() == 'job overview':
                        short_desc = desc.context
                        break
                # Fallback to first description if "Job Overview" not found
                if short_desc == "View details to learn more about this role.":
                     short_desc = job_orm.descriptions[0].context
            
            job_data["short_description"] = short_desc[:250] + '...' if len(short_desc) > 250 else short_desc

            formatted_jobs.append(job_data)

        return formatted_jobs