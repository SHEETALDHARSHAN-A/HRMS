# src/db/repository/curation_repository.py

import json

from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Dict, Optional

from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func

from src.db.models.curation_model import Curation
from src.db.models.shortlist_model import Shortlist
from src.db.models.resume_model import Profile, InterviewRounds

from src.db.models.job_post_model import (
    JobDetails, JobSkills, SkillList,
    JobLocations, LocationList, RoundList,
    EvaluationCriteria, JobDescription
)

class CurationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_job_configuration(self, job_id: UUID) -> Optional[JobDetails]:
        """
        Fetch JobDetails and eagerly load related metadata.
        """
        stmt = (
            select(JobDetails)
            .filter(JobDetails.id == job_id)
            .options(
                selectinload(JobDetails.job_skills).selectinload(JobSkills.skill),
                selectinload(JobDetails.locations).selectinload(JobLocations.location),
                selectinload(JobDetails.rounds).selectinload(RoundList.evaluation_criteria),
                selectinload(JobDetails.descriptions)
            )
        )
        result = await self.session.execute(stmt)
        job = result.scalars().first()

        # Attach flattened location data for easier use
        if job and getattr(job, "locations", None):
            # NOTE: Assuming location object has 'location_name', 'state', 'country'
            job.location_details = [
                {
                    "location_name": getattr(loc.location, "location", None), # Corrected potential attribute name
                    "state": getattr(loc.location, "state", None),
                    "country": getattr(loc.location, "country", None),
                }
                for loc in job.locations
                if getattr(loc, "location", None)
            ]
        else:
            job.location_details = []

        # FIX: Flatten job descriptions using the correct 'context' attribute
        if job and getattr(job, "descriptions", None):
            job.full_description_text = "\n\n".join([
                desc.context or "" for desc in job.descriptions 
            ])
        else:
            job.full_description_text = getattr(job, "job_description", "") # Fallback if no linked descriptions

        return job

    async def fetch_profiles(self, job_id: UUID, profile_ids: Optional[List[str]] = None) -> List[Profile]:
        """
        Fetch profiles for this job, optionally filtering by profile_ids.
        """
        stmt = select(Profile).filter(Profile.job_id == job_id)
        
        if profile_ids:
            try:
                # Filter the query directly in the DB for efficiency
                uuid_ids = [UUID(pid) for pid in profile_ids]
                stmt = stmt.filter(Profile.id.in_(uuid_ids))
            except (ValueError, TypeError) as e:
                raise RuntimeError(f"Invalid UUID in profile_ids list: {e}") from e
            
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def fetch_first_round(self, job_id: UUID) -> Optional[RoundList]:
        """Fetch the first round (screening/curation) for the given job."""
        stmt = select(RoundList).filter(RoundList.job_id == job_id, RoundList.round_order == 1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save_curation_results(self, curated_data: List[Dict[str, any]]) -> List[Curation]:
        """
        Insert-only curation + shortlist per profile.
        Does NOT update JobDetails summary counts.
        """
        try:
            if not curated_data:
                return []

            now = datetime.now(timezone.utc)
            created_curations: List[Curation] = []

            job_id_for_round = curated_data[0]["job_id"]
            first_round = await self.fetch_first_round(job_id_for_round)

            for data in curated_data:
                job_id = data["job_id"]
                profile_id = data["profile_id"]

                # Ensure skill_score_explanation is JSON-friendly
                try:
                    explanation_json = (
                        data.get("skill_score_explanation")
                        if isinstance(data.get("skill_score_explanation"), (dict, list))
                        else json.loads(data.get("skill_score_explanation", "{}"))
                    )
                except Exception:
                    explanation_json = {}

                # Skip if already curated
                stmt = select(Curation).filter(
                    Curation.job_id == job_id,
                    Curation.profile_id == profile_id
                )
                res = await self.session.execute(stmt)
                if res.scalars().first():
                    continue

                # Insert new curation entry
                curation_obj = Curation(
                    id=uuid4(),
                    job_id=job_id,
                    profile_id=profile_id,
                    potential_score=data.get("potential_score", 0),
                    location_score=data.get("location_score", 0),
                    role_fit_score=data.get("role_fit_score", 0),
                    skill_score=data.get("skill_score", 0),
                    skill_score_explanation=explanation_json,
                    created_at=now,
                )
                self.session.add(curation_obj)
                await self.session.flush()
                created_curations.append(curation_obj)

                # Insert or link shortlist
                stmt_s = select(Shortlist).filter(
                    Shortlist.job_id == job_id,
                    Shortlist.profile_id == profile_id
                )
                res_s = await self.session.execute(stmt_s)
                existing_short = res_s.scalars().first()

                if existing_short:
                    if not existing_short.curation_id:
                        existing_short.curation_id = curation_obj.id
                        existing_short.updated_at = now
                else:
                    new_short = Shortlist(
                        id=uuid4(),
                        job_id=job_id,
                        profile_id=profile_id,
                        curation_id=curation_obj.id,
                        overall_score=data.get("overall_score", 0),
                        score_explanation=data.get("explanation", ""),
                        result=data.get("result", "under_review"),
                        created_at=now,
                        updated_at=now,
                    )
                    self.session.add(new_short)

                # Update InterviewRounds status for the first round
                if first_round:
                    await self.session.execute(
                        update(InterviewRounds)
                        .filter(
                            InterviewRounds.job_id == job_id,
                            InterviewRounds.profile_id == profile_id,
                            InterviewRounds.round_id == first_round.id,
                        )
                        .values(status=data.get("result", "under_review"))
                    )

            # Commit all inserts/updates
            await self.session.commit()
            return created_curations

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Error saving curation results: {str(e)}")
