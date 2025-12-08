# src/db/repository/resume_repository.py

from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Set, Dict, Any, Optional 

from src.db.models.job_post_model import JobDetails, RoundList
from src.db.models.resume_model import Profile, InterviewRounds


class ResumeRepository:
    """Handles resume insertion and initialization of interview rounds."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # FIX APPLIED HERE: Changed return type from Set[str] to Dict[str, str]
    async def get_existing_hashes_for_job(self, job_id: UUID) -> Dict[str, str]:
        """Fetch all file hashes for the given job to prevent duplicates."""
        stmt = select(Profile.file_hash, Profile.id).filter(Profile.job_id == job_id)
        result = await self.session.execute(stmt)
        
        # Changed logic: Map hash (key) to profile ID (value) or hash (value) if only existence check is needed.
        # Mapping to hash (as a placeholder for existence) is sufficient to fix the TypeError.
        # Let's map hash to the hash itself, or optionally to the profile ID. Using the hash for simplicity.
        return {
            hash_val: str(profile_id) # Map hash to profile ID for better error reporting upstream
            for hash_val, profile_id in result.all()
            if hash_val is not None
        }

    # ------------------------------------------------------------------
    async def check_job_details_exists(self, job_id: UUID) -> bool:
        """
        [NEW METHOD] Check if a JobDetails entry exists for the given job_id.
        This prevents the Foreign Key violation during Profile insertion.
        """
        stmt = select(JobDetails.id).filter(JobDetails.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    async def get_first_round_id(self, job_id: UUID) -> Optional[UUID]:
        """Fetch the first round ID (round_order = 1) for the given job."""
        stmt = (
            select(RoundList.id)
            .where(RoundList.job_id == job_id, RoundList.round_order == 1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    async def create_resumes(self, resume_data_list: List[Dict[str, Any]]) -> List[Profile]:
        """
        Insert multiple resume entries, auto-create interview_rounds entries
        for round_order = 1, and update total_candidates in JobDetails.
        """
        records: List[Profile] = []
        job_ids_to_update = set()

        try:
            for data in resume_data_list:
                job_id = data["job_id"]

                # --- FIX FOR FOREIGN KEY VIOLATION (SECONDARY CHECK) ---
                if not await self.check_job_details_exists(job_id):
                    print(f"[ERROR] Job ID {job_id} not found in JobDetails. Skipping profile creation for file: {data.get('file_name', 'N/A')}")
                    continue
                # -----------------------------------------------------

                round_id = await self.get_first_round_id(job_id)

                profile = Profile(
                    job_id=job_id,
                    name=data.get("name"),
                    email=data.get("email"),
                    phone_number=data.get("phone"),
                    file_name=data["file_name"],
                    file_type=data["file_type"],
                    file_hash=data.get("file_hash"),
                    extracted_content=data["extracted_content"],
                    created_at=datetime.now(timezone.utc),
                )

                # Optional: resume link
                if data.get("resume_link"):
                    profile.resume_link = data["resume_link"]

                self.session.add(profile)
                await self.session.flush()

                # Auto-create first round entry if available
                if round_id:
                    interview_round = InterviewRounds(
                        job_id=job_id,
                        profile_id=profile.id,
                        round_id=round_id,
                        status="pending",
                    )
                    self.session.add(interview_round)

                records.append(profile)
                job_ids_to_update.add(job_id)

            # Update total_candidates count in JobDetails safely
            for job_id_to_update in job_ids_to_update:
                total_candidates_stmt = select(func.count(Profile.id)).where(Profile.job_id == job_id_to_update)
                result = await self.session.execute(total_candidates_stmt)
                total_candidates = result.scalar() or 0

                update_stmt = (
                    update(JobDetails)
                    .where(JobDetails.id == job_id_to_update)
                    .values(
                        total_candidates=total_candidates,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await self.session.execute(update_stmt)
                print(f"[INFO] Updated total_candidates = {total_candidates} for Job ID {job_id_to_update}")


            await self.session.commit()
            return records

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Error creating resumes: {str(e)}")

# # src/db/repository/resume_repository.py

# from uuid import UUID
# from datetime import datetime, timezone
# from sqlalchemy.exc import SQLAlchemyError
# from sqlalchemy import select, func, update
# from sqlalchemy.ext.asyncio import AsyncSession
# from typing import List, Set, Dict, Any, Optional 

# from src.db.models.job_post_model import JobDetails, RoundList
# from src.db.models.resume_model import Profile, InterviewRounds


# class ResumeRepository:
#     """Handles resume insertion and initialization of interview rounds."""

#     def __init__(self, session: AsyncSession):
#         self.session = session

#     # ------------------------------------------------------------------
#     async def get_existing_hashes_for_job(self, job_id: UUID) -> Set[str]:
#         """Fetch all file hashes for the given job to prevent duplicates."""
#         stmt = select(Profile.file_hash).filter(Profile.job_id == job_id)
#         result = await self.session.execute(stmt)
#         return set(result.scalars().all())

#     # ------------------------------------------------------------------
#     async def check_job_details_exists(self, job_id: UUID) -> bool:
#         """
#         [NEW METHOD] Check if a JobDetails entry exists for the given job_id.
#         This prevents the Foreign Key violation during Profile insertion.
#         """
#         stmt = select(JobDetails.id).filter(JobDetails.id == job_id)
#         result = await self.session.execute(stmt)
#         return result.scalar_one_or_none() is not None

#     # ------------------------------------------------------------------
#     async def get_first_round_id(self, job_id: UUID) -> Optional[UUID]:
#         """Fetch the first round ID (round_order = 1) for the given job."""
#         stmt = (
#             select(RoundList.id)
#             .where(RoundList.job_id == job_id, RoundList.round_order == 1)
#         )
#         result = await self.session.execute(stmt)
#         return result.scalar_one_or_none()

#     # ------------------------------------------------------------------
#     async def create_resumes(self, resume_data_list: List[Dict[str, Any]]) -> List[Profile]:
#         """
#         Insert multiple resume entries, auto-create interview_rounds entries
#         for round_order = 1, and update total_candidates in JobDetails.
#         """
#         records: List[Profile] = []
#         job_ids_to_update = set()

#         try:
#             for data in resume_data_list:
#                 job_id = data["job_id"]

#                 # --- FIX FOR FOREIGN KEY VIOLATION (SECONDARY CHECK) ---
#                 if not await self.check_job_details_exists(job_id):
#                     print(f"[ERROR] Job ID {job_id} not found in JobDetails. Skipping profile creation for file: {data.get('file_name', 'N/A')}")
#                     continue
#                 # -----------------------------------------------------

#                 round_id = await self.get_first_round_id(job_id)

#                 profile = Profile(
#                     job_id=job_id,
#                     name=data.get("name"),
#                     email=data.get("email"),
#                     phone_number=data.get("phone"),
#                     file_name=data["file_name"],
#                     file_type=data["file_type"],
#                     file_hash=data.get("file_hash"),
#                     extracted_content=data["extracted_content"],
#                     created_at=datetime.now(timezone.utc),
#                 )

#                 # Optional: resume link
#                 if data.get("resume_link"):
#                     profile.resume_link = data["resume_link"]

#                 self.session.add(profile)
#                 await self.session.flush()

#                 # Auto-create first round entry if available
#                 if round_id:
#                     interview_round = InterviewRounds(
#                         job_id=job_id,
#                         profile_id=profile.id,
#                         round_id=round_id,
#                         status="pending",
#                     )
#                     self.session.add(interview_round)

#                 records.append(profile)
#                 job_ids_to_update.add(job_id)

#             # Update total_candidates count in JobDetails safely
#             for job_id_to_update in job_ids_to_update:
#                 total_candidates_stmt = select(func.count(Profile.id)).where(Profile.job_id == job_id_to_update)
#                 result = await self.session.execute(total_candidates_stmt)
#                 total_candidates = result.scalar() or 0

#                 update_stmt = (
#                     update(JobDetails)
#                     .where(JobDetails.id == job_id_to_update)
#                     .values(
#                         total_candidates=total_candidates,
#                         updated_at=datetime.now(timezone.utc),
#                     )
#                 )
#                 await self.session.execute(update_stmt)
#                 print(f"[INFO] Updated total_candidates = {total_candidates} for Job ID {job_id_to_update}")


#             await self.session.commit()
#             return records

#         except SQLAlchemyError as e:
#             await self.session.rollback()
#             raise RuntimeError(f"Error creating resumes: {str(e)}")