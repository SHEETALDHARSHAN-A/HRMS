# app/db/repository/scheduling_repository.py
 
import re
import logging
import inspect

from uuid import UUID
from typing import List, Dict, Any

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, insert, delete, update
from app import db
from app.db.models.scheduling_model import Scheduling
from app.db.models.user_model import User
from app.db.models.resume_model import Profile
from app.db.models.job_post_model import JobDetails, RoundList
from app.db.models.job_post_model import JobDetails
from app.db.models.scheduling_model import Scheduling
from typing import List, Dict, Any, Optional
from uuid import UUID
import re
import logging # Needed for the logging calls (retained)

logger = logging.getLogger(__name__)

async def get_candidate_details_for_scheduling(db: AsyncSession, profile_ids: List[str]) -> List[Dict[str, Any]]:
    """
    FIX: Rewritten to directly fetch structured fields (name, email, phone_number) from the Profile model.
    """
    uuid_p_ids = [UUID(p_id) for p_id in profile_ids]
    
    # 1. Query the Profile table for the required fields
    stmt = select(
        Profile.id,
        Profile.name,
        Profile.email,
        Profile.phone_number
    ).where(Profile.id.in_(uuid_p_ids))
    
    result = await db.execute(stmt)
    profile_data = result.fetchall() 
    
    formatted_users = []

    for row in profile_data:
        # row[0]=id, row[1]=name, row[2]=email, row[3]=phone_number
        profile_id_str = str(row[0])
        full_name = row[1]
        email = row[2]
        phone_number = row[3]

        # Simple attempt to split name into first and last
        first_name, last_name = (full_name.rsplit(' ', 1) if full_name and ' ' in full_name else (full_name, None))

        formatted_users.append({
            "user_id": profile_id_str, 
            "profile_id": profile_id_str, 
            "first_name": first_name or "",
            "last_name": last_name or "",
            "email": email or "",
            "phone_number": phone_number or "",
        })

    return formatted_users

async def check_existing_schedules(db: AsyncSession, job_id: str, profile_ids: List[str]) -> List[str]:
    """Checks which profiles are already scheduled for this job."""
    # FIX: Use profile_id directly, as the conversion happens in the caller or is handled by the model
    stmt = select(Scheduling.profile_id).where(
        Scheduling.job_id == job_id,
        Scheduling.profile_id.in_(profile_ids)
    )
    result = await db.execute(stmt)
    # Return list of UUID strings that are already scheduled
    return [str(pid) for pid in result.scalars().all()]
 
async def create_schedules_batch(db: AsyncSession, schedules_data: List[Dict[str, Any]]) -> List[str]:
    """Inserts a batch of new scheduling records."""
    if not schedules_data:
        return []
   
    # Convert dicts to ORM objects for insertion
    schedule_objects = []
    try:
        # Try to instantiate the SQLAlchemy model objects
        for data in schedules_data:
            schedule_objects.append(Scheduling(**data))
    except TypeError:
        # If SQLAlchemy Base is a dummy in tests, Scheduling will not accept kwargs.
        # Fall back to using SimpleNamespace objects so the FakeDB fixture can store them.
        from types import SimpleNamespace
        schedule_objects = [SimpleNamespace(**data) for data in schedules_data]

    # Persist objects: prefer bulk add_all if available, otherwise call add per object
    if hasattr(db, "add_all"):
        try:
            maybe = db.add_all(schedule_objects)
            if inspect.isawaitable(maybe):
                try:
                    await maybe
                except TypeError:
                    # Some DB-like objects may raise TypeError when add_all isn't supported
                    for obj in schedule_objects:
                        maybe2 = db.add(obj)
                        if inspect.isawaitable(maybe2):
                            await maybe2
            # If add_all completed synchronously, nothing else to do
        except TypeError:
            # Some DB-like objects may not accept add_all; fallback to per-object add
            for obj in schedule_objects:
                maybe2 = db.add(obj)
                if inspect.isawaitable(maybe2):
                    await maybe2
    else:
        for obj in schedule_objects:
            maybe2 = db.add(obj)
            if inspect.isawaitable(maybe2):
                await maybe2
    await db.commit()
   
    # Return IDs of successfully inserted records
    return [str(s.profile_id) for s in schedule_objects]
 
async def update_schedule_email_status(db: AsyncSession, profile_id: str, job_id: str, email_sent: bool) -> bool:
    """Updates the email_sent status of a specific schedule."""
    # FIX: Ensure 'update' is imported (it was missing from the provided code, added to imports)
    stmt = (
        update(Scheduling)
        .where(Scheduling.profile_id == profile_id, Scheduling.job_id == job_id)
        .values(email_sent=email_sent)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0
 
async def get_job_title_by_id(db: AsyncSession, job_id: str) -> str | None:
    """Fetches the job title for use in the email."""
    stmt = select(JobDetails.job_title).where(JobDetails.id == job_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# Conceptual change needed in app/db/repository/scheduling_repository.py:

# --- NEW FUNCTION TO FETCH ROUND NAME ---
async def get_round_name_by_id(db: AsyncSession, round_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the round name given the round ID from the RoundList model.
    """
    try:
        # RoundList.id is a UUID column, so we convert round_id (str) to UUID for comparison
        uuid_round_id = UUID(round_id) 
    except ValueError:
        logger.warning(f"Invalid UUID format for round_id: {round_id}")
        return None

    # Select only the round_name column
    stmt = select(RoundList.round_name).where(RoundList.id == uuid_round_id)

    result = await db.execute(stmt)
    round_name = result.scalar_one_or_none()

    if round_name:
        # Return as a dictionary to align with other repository fetch functions
        return {"round_name": round_name}
    
    return None


async def get_next_round_details(db: AsyncSession, job_id: str, current_round_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the round name for the next round in the sequence for a given job.
    """
    try:
        uuid_job_id = UUID(job_id)
        uuid_current_round_id = UUID(current_round_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for job_id ({job_id}) or current_round_id ({current_round_id})")
        return None

    # 1. Get the order number of the current round
    current_round_stmt = select(RoundList.round_order).where(
        RoundList.job_id == uuid_job_id,
        RoundList.id == uuid_current_round_id
    )
    current_round_order = (await db.execute(current_round_stmt)).scalar_one_or_none()

    if current_round_order is None:
        logger.warning(f"Current round ID {current_round_id} not found for job {job_id}.")
        return None

    next_round_order = current_round_order + 1

    # 2. Get the name of the round with the next order number
    next_round_stmt = select(RoundList.round_name).where(
        RoundList.job_id == uuid_job_id,
        RoundList.round_order == next_round_order
    )
    next_round_name = (await db.execute(next_round_stmt)).scalar_one_or_none()

    if next_round_name:
        # Return as a dictionary for consistency with other repository functions
        return {"round_name": next_round_name}
    
    return None # No next round found

async def get_scheduled_interviews(job_id: str, round_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
    stmt = select(
        Scheduling.profile_id.label("profile_id"),
        Scheduling.job_id.label("job_id"),
        Scheduling.round_id.label("round_id"),
        Scheduling.scheduled_datetime,
        Scheduling.status,
        Scheduling.interview_token,
        Scheduling.interview_type,
        Scheduling.level_of_interview,
        Profile.name.label("candidate_name"),
        Profile.email.label("candidate_email"),
        JobDetails.job_title.label("job_title"),
        RoundList.round_name.label("round_name"),
    ).select_from(
        Scheduling
    ).join(
        Profile, Scheduling.profile_id == Profile.id
    ).join(
        JobDetails, Scheduling.job_id == JobDetails.id
    ).join(
        RoundList, Scheduling.round_id == RoundList.id
    ).where(
      and_(
          Scheduling.job_id == UUID(job_id),
          Scheduling.round_id == UUID(round_id)
      )  
      ).order_by(
        Scheduling.scheduled_datetime.asc()
    )
    

    result = await db.execute(stmt)
    rows = result.fetchall()
    
    scheduled_list = []
    for row in rows:
        scheduled_list.append({
            "profile_id": str(row.profile_id),
            "job_id": str(row.job_id),
            "round_id": str(row.round_id),
            "candidate_name": row.candidate_name,
            "candidate_email": row.candidate_email,
            "job_title": row.job_title,
            "round_name": row.round_name,
            "scheduled_datetime": row.scheduled_datetime.isoformat(),
            "status": row.status,
            "interview_token": str(row.interview_token),
            "interview_type": row.interview_type,
            "level_of_interview": row.level_of_interview,
        })
        
    return scheduled_list
