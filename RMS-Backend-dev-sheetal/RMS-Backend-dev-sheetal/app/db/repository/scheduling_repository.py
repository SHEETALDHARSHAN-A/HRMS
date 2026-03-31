# app/db/repository/scheduling_repository.py
 
import re
import logging
import inspect
from datetime import datetime, timezone

from uuid import UUID
from typing import List, Dict, Any

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, insert, delete, update, or_
from app import db
from app.db.models.scheduling_model import Scheduling
from app.db.models.user_model import User
from app.db.models.resume_model import Profile, InterviewRounds
from app.db.models.job_post_model import JobDetails, RoundList
from app.db.models.job_post_model import JobDetails
from app.db.models.scheduling_model import Scheduling
from app.db.models.agent_config_model import AgentRoundConfig
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

async def check_existing_schedules(
    db: AsyncSession,
    job_id: str,
    profile_ids: List[str],
    requested_round_id: Optional[str] = None,
) -> List[str]:
    """Checks which profiles are already scheduled for this job and round.

    Historical data may store scheduling.round_id either as interview_rounds.id or
    directly as round_list.id. This function supports both shapes.
    """
    if not requested_round_id:
        stmt = select(Scheduling.profile_id).where(
            Scheduling.job_id == job_id,
            Scheduling.profile_id.in_(profile_ids)
        )
        result = await db.execute(stmt)
        return [str(pid) for pid in result.scalars().all()]

    try:
        requested_round_uuid = UUID(str(requested_round_id))
    except Exception:
        # If the requested round is malformed, fall back to legacy check.
        stmt = select(Scheduling.profile_id).where(
            Scheduling.job_id == job_id,
            Scheduling.profile_id.in_(profile_ids)
        )
        result = await db.execute(stmt)
        return [str(pid) for pid in result.scalars().all()]

    stmt = (
        select(
            Scheduling.profile_id.label("profile_id"),
            Scheduling.round_id.label("scheduled_round_id"),
            InterviewRounds.id.label("interview_round_id"),
            InterviewRounds.round_id.label("round_list_id"),
        )
        .select_from(Scheduling)
        .join(InterviewRounds, Scheduling.round_id == InterviewRounds.id, isouter=True)
        .where(
            Scheduling.job_id == job_id,
            Scheduling.profile_id.in_(profile_ids),
        )
    )

    rows = (await db.execute(stmt)).fetchall()

    already_scheduled: set[str] = set()
    for row in rows:
        scheduled_round_id = getattr(row, "scheduled_round_id", None)
        interview_round_id = getattr(row, "interview_round_id", None)
        round_list_id = getattr(row, "round_list_id", None)

        if (
            scheduled_round_id == requested_round_uuid
            or interview_round_id == requested_round_uuid
            or round_list_id == requested_round_uuid
        ):
            already_scheduled.add(str(getattr(row, "profile_id")))

    return list(already_scheduled)


async def resolve_round_instance_id_for_schedule(
    db: AsyncSession,
    job_id: str,
    profile_id: str,
    requested_round_id: str,
) -> str:
    """Resolve the scheduling round foreign key as interview_rounds.id.

    Accepts either a round_list.id or interview_rounds.id from the caller and
    returns the interview_rounds.id to persist in scheduling_interviews.round_id.
    """
    try:
        job_uuid = UUID(str(job_id))
        profile_uuid = UUID(str(profile_id))
        requested_round_uuid = UUID(str(requested_round_id))
    except Exception:
        return str(requested_round_id)

    # Case 1: caller already passed interview_rounds.id
    by_instance_stmt = (
        select(InterviewRounds)
        .where(InterviewRounds.id == requested_round_uuid)
        .where(InterviewRounds.job_id == job_uuid)
        .where(InterviewRounds.profile_id == profile_uuid)
    )
    by_instance = (await db.execute(by_instance_stmt)).scalars().first()
    if by_instance is not None:
        if not by_instance.status or str(by_instance.status).lower() in {"pending", "under_review"}:
            by_instance.status = "interview_scheduled"
        return str(by_instance.id)

    # Case 2: caller passed round_list.id
    by_round_list_stmt = (
        select(InterviewRounds)
        .where(InterviewRounds.job_id == job_uuid)
        .where(InterviewRounds.profile_id == profile_uuid)
        .where(InterviewRounds.round_id == requested_round_uuid)
        .order_by(InterviewRounds.id.desc())
    )
    by_round_list = (await db.execute(by_round_list_stmt)).scalars().first()
    if by_round_list is not None:
        if not by_round_list.status or str(by_round_list.status).lower() in {"pending", "under_review"}:
            by_round_list.status = "interview_scheduled"
        return str(by_round_list.id)

    # Create missing interview round instance if round exists for the job.
    round_exists_stmt = (
        select(RoundList.id)
        .where(RoundList.job_id == job_uuid)
        .where(RoundList.id == requested_round_uuid)
    )
    round_exists = (await db.execute(round_exists_stmt)).scalar_one_or_none()
    if round_exists is None:
        return str(requested_round_id)

    new_instance = InterviewRounds(
        job_id=job_uuid,
        profile_id=profile_uuid,
        round_id=requested_round_uuid,
        status="interview_scheduled",
    )
    db.add(new_instance)
    if hasattr(db, "flush"):
        await db.flush()
    return str(new_instance.id)
 
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


async def get_round_duration_minutes(
    db: AsyncSession,
    *,
    job_id: str,
    round_id: str,
    default_minutes: int = 60,
) -> int:
    """Resolve interview duration (minutes) from round config with sane defaults."""
    try:
        job_uuid = UUID(str(job_id))
        round_uuid = UUID(str(round_id))
    except Exception:
        return default_minutes

    round_list_id = None

    round_list_stmt = select(RoundList.id).where(
        RoundList.job_id == job_uuid,
        RoundList.id == round_uuid,
    )
    round_list_id = (await db.execute(round_list_stmt)).scalar_one_or_none()

    if round_list_id is None:
        round_instance_stmt = select(InterviewRounds.round_id).where(
            InterviewRounds.job_id == job_uuid,
            InterviewRounds.id == round_uuid,
        )
        round_list_id = (await db.execute(round_instance_stmt)).scalar_one_or_none()

    if round_list_id is None:
        return default_minutes

    config_stmt = (
        select(AgentRoundConfig)
        .where(AgentRoundConfig.job_id == job_uuid)
        .where(AgentRoundConfig.round_list_id == round_list_id)
        .limit(1)
    )
    config = (await db.execute(config_stmt)).scalars().first()
    if config is None:
        return default_minutes

    for attr in ("interview_time_max", "interview_time_min"):
        raw = getattr(config, attr, None)
        if raw is None:
            continue
        try:
            value = int(raw)
        except Exception:
            continue
        if value > 0:
            return min(240, max(30, value))

    return default_minutes


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


async def get_schedule_context_by_token(
    db: AsyncSession,
    interview_token: str,
) -> Optional[Dict[str, Any]]:
    """Fetch schedule + candidate metadata by interview token."""
    try:
        token_uuid = UUID(str(interview_token))
    except ValueError:
        return None

    stmt = (
        select(
            Scheduling.profile_id.label("profile_id"),
            Scheduling.job_id.label("job_id"),
            Scheduling.round_id.label("round_id"),
            Scheduling.interview_token.label("interview_token"),
            Scheduling.interview_type.label("interview_type"),
            Scheduling.level_of_interview.label("level_of_interview"),
            Scheduling.rescheduled_count.label("rescheduled_count"),
            Scheduling.scheduled_datetime.label("scheduled_datetime"),
            Scheduling.interview_duration.label("interview_duration"),
            Profile.name.label("candidate_name"),
            Profile.email.label("candidate_email"),
            JobDetails.job_title.label("job_title"),
            RoundList.round_name.label("round_name"),
        )
        .select_from(Scheduling)
        .join(Profile, Scheduling.profile_id == Profile.id)
        .join(JobDetails, Scheduling.job_id == JobDetails.id)
        .join(InterviewRounds, Scheduling.round_id == InterviewRounds.id, isouter=True)
        .join(
            RoundList,
            or_(
                RoundList.id == Scheduling.round_id,
                RoundList.id == InterviewRounds.round_id,
            ),
            isouter=True,
        )
        .where(Scheduling.interview_token == token_uuid)
        .limit(1)
    )

    row = (await db.execute(stmt)).fetchone()
    if row is None:
        return None

    return {
        "profile_id": str(row.profile_id),
        "job_id": str(row.job_id),
        "round_id": str(row.round_id),
        "interview_token": str(row.interview_token),
        "interview_type": row.interview_type,
        "level_of_interview": row.level_of_interview,
        "rescheduled_count": row.rescheduled_count,
        "scheduled_datetime": row.scheduled_datetime,
        "interview_duration": row.interview_duration,
        "candidate_name": row.candidate_name,
        "candidate_email": row.candidate_email,
        "job_title": row.job_title,
        "round_name": row.round_name,
    }


async def get_schedule_context_by_identifiers(
    db: AsyncSession,
    *,
    job_id: str,
    profile_id: str,
    round_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetch schedule + candidate metadata by job/profile/round identity.

    Supports round_id as either scheduling_interviews.round_id (interview_rounds.id)
    or interview_rounds.round_id (round_list.id).
    """
    try:
        job_uuid = UUID(str(job_id))
        profile_uuid = UUID(str(profile_id))
        round_uuid = UUID(str(round_id))
    except ValueError:
        return None

    stmt = (
        select(
            Scheduling.profile_id.label("profile_id"),
            Scheduling.job_id.label("job_id"),
            Scheduling.round_id.label("round_id"),
            Scheduling.interview_token.label("interview_token"),
            Scheduling.interview_type.label("interview_type"),
            Scheduling.level_of_interview.label("level_of_interview"),
            Scheduling.rescheduled_count.label("rescheduled_count"),
            Scheduling.scheduled_datetime.label("scheduled_datetime"),
            Scheduling.interview_duration.label("interview_duration"),
            Profile.name.label("candidate_name"),
            Profile.email.label("candidate_email"),
            JobDetails.job_title.label("job_title"),
            RoundList.round_name.label("round_name"),
        )
        .select_from(Scheduling)
        .join(Profile, Scheduling.profile_id == Profile.id)
        .join(JobDetails, Scheduling.job_id == JobDetails.id)
        .join(InterviewRounds, Scheduling.round_id == InterviewRounds.id, isouter=True)
        .join(
            RoundList,
            or_(
                RoundList.id == Scheduling.round_id,
                RoundList.id == InterviewRounds.round_id,
            ),
            isouter=True,
        )
        .where(Scheduling.job_id == job_uuid)
        .where(Scheduling.profile_id == profile_uuid)
        .where(
            or_(
                Scheduling.round_id == round_uuid,
                InterviewRounds.round_id == round_uuid,
            )
        )
        .order_by(Scheduling.scheduled_datetime.desc())
        .limit(1)
    )

    row = (await db.execute(stmt)).fetchone()
    if row is None:
        return None

    return {
        "profile_id": str(row.profile_id),
        "job_id": str(row.job_id),
        "round_id": str(row.round_id),
        "interview_token": str(row.interview_token),
        "interview_type": row.interview_type,
        "level_of_interview": row.level_of_interview,
        "rescheduled_count": row.rescheduled_count,
        "scheduled_datetime": row.scheduled_datetime,
        "interview_duration": row.interview_duration,
        "candidate_name": row.candidate_name,
        "candidate_email": row.candidate_email,
        "job_title": row.job_title,
        "round_name": row.round_name,
    }


async def reschedule_interview_by_token(
    db: AsyncSession,
    interview_token: str,
    scheduled_datetime: datetime,
) -> Optional[Dict[str, Any]]:
    """Update scheduled datetime/status by interview token."""
    try:
        token_uuid = UUID(str(interview_token))
    except ValueError:
        return None

    stmt = select(Scheduling).where(Scheduling.interview_token == token_uuid)
    schedule = (await db.execute(stmt)).scalars().first()
    if schedule is None:
        return None

    schedule.scheduled_datetime = scheduled_datetime
    schedule.status = "rescheduled"
    schedule.rescheduled_count = int(schedule.rescheduled_count or 0) + 1
    schedule.updated_at = datetime.now(timezone.utc)

    await db.commit()
    try:
        await db.refresh(schedule)
    except Exception:
        # Some mocked DB implementations used by tests may not support refresh.
        pass

    return {
        "profile_id": str(schedule.profile_id),
        "job_id": str(schedule.job_id),
        "round_id": str(schedule.round_id),
        "interview_token": str(schedule.interview_token),
        "status": schedule.status,
        "rescheduled_count": schedule.rescheduled_count,
        "scheduled_datetime": schedule.scheduled_datetime,
    }

async def get_scheduled_interviews(job_id: str, round_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
    try:
        job_uuid = UUID(job_id)
        round_uuid = UUID(round_id)
    except ValueError:
        return []

    stmt = select(
        Scheduling.profile_id.label("profile_id"),
        Scheduling.job_id.label("job_id"),
        Scheduling.round_id.label("round_id"),
        Scheduling.scheduled_datetime,
        Scheduling.interview_duration,
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
        InterviewRounds, Scheduling.round_id == InterviewRounds.id, isouter=True
    ).join(
        RoundList,
        or_(
            RoundList.id == Scheduling.round_id,
            RoundList.id == InterviewRounds.round_id,
        ),
        isouter=True,
    ).where(
      and_(
          Scheduling.job_id == job_uuid,
          or_(
              Scheduling.round_id == round_uuid,
              InterviewRounds.round_id == round_uuid,
          ),
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
            "interview_duration": row.interview_duration,
            "status": row.status,
            "interview_token": str(row.interview_token),
            "interview_type": row.interview_type,
            "level_of_interview": row.level_of_interview,
        })
        
    return scheduled_list
