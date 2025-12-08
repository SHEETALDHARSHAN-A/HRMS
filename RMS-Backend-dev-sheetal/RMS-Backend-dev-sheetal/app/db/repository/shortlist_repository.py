# app/db/repositroy/shortlist_repository.py

import logging

from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, case, asc, func, update

from app.db.models.curation_model import Curation
from app.db.models.shortlist_model import Shortlist
from app.db.models.job_post_model import JobDetails, RoundList
from app.db.models.resume_model import Profile, InterviewRounds

logger = logging.getLogger(__name__)

async def get_job_round_overview(db: AsyncSession) -> List[Dict[str, Any]]:
    """List all jobs with their rounds and candidate status counts."""
    shortlisted_case = case((InterviewRounds.status == "shortlisted", 1), else_=0)
    under_review_case = case((InterviewRounds.status == "under_review", 1), else_=0)
    rejected_case = case((InterviewRounds.status == "rejected", 1), else_=0)

    stmt = (
        select(
            JobDetails.id.label("job_id"),
            JobDetails.job_title,
            RoundList.id.label("round_id"),
            RoundList.round_name,
            RoundList.round_order,
            func.count(InterviewRounds.profile_id).label("total_candidates"),
            func.sum(shortlisted_case).label("shortlisted"),
            func.sum(under_review_case).label("under_review"),
            func.sum(rejected_case).label("rejected"),
        )
        .select_from(JobDetails)
        .join(RoundList, JobDetails.id == RoundList.job_id, isouter=True)
        .join(InterviewRounds, RoundList.id == InterviewRounds.round_id, isouter=True)
        .group_by(JobDetails.id, JobDetails.job_title, RoundList.id, RoundList.round_name, RoundList.round_order)
        .order_by(asc(JobDetails.job_title), asc(RoundList.round_order))
    )

    res = await db.execute(stmt)
    rows = res.fetchall()
    formatted = []

    for r in rows:
        if r.round_id is None:
            continue
        formatted.append({
            "job_id": str(r.job_id),
            "job_title": r.job_title,
            "round_id": str(r.round_id),
            "round_name": r.round_name,
            "round_order": r.round_order,
            "total_candidates": r.total_candidates or 0,
            "shortlisted": r.shortlisted or 0,
            "under_review": r.under_review or 0,
            "rejected": r.rejected or 0,
        })

    return formatted

async def update_interview_round_status(
    db: AsyncSession,
    profile_id: str,
    round_id: str,
    new_status: str,
) -> bool:
    """Update interview round status for a profile."""
    stmt = (
        update(InterviewRounds)
        .where(and_(
            InterviewRounds.profile_id == profile_id,
            InterviewRounds.round_id == round_id,
        ))
        .values(status=new_status)
        .execution_options(synchronize_session="fetch")
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_round_candidates(
    db: AsyncSession,
    job_id: str,
    round_id: str,
    result_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch candidates for a specific round and job."""
    filters = [
        Shortlist.job_id == job_id,
        InterviewRounds.round_id == round_id,
        Shortlist.profile_id == InterviewRounds.profile_id,
    ]

    if result_filter and result_filter.lower() != "all":
        filters.append(Shortlist.result == result_filter.lower())

    order_by_case = case(
        (Shortlist.result == "shortlist", 1),
        (Shortlist.result == "under_review", 2),
        (Shortlist.result == "reject", 3),
        else_=4
    )

    stmt = (
        select(
            Profile.id.label("profile_id"),
            Profile.name.label("candidate_name"),
            Profile.email.label("candidate_email"),
            Profile.extracted_content.label("resume_data"),
            Shortlist.result,
            Shortlist.overall_score,
            Shortlist.score_explanation,
            Shortlist.reason,
            Curation.potential_score,
            Curation.location_score,
            Curation.role_fit_score,
            Curation.skill_score,
            Curation.skill_score_explanation,
            InterviewRounds.status.label("round_status"),
            RoundList.round_name.label("round_name")
        )
        .select_from(Shortlist)
        .join(Profile, Shortlist.profile_id == Profile.id)
        .join(Curation, Shortlist.curation_id == Curation.id)
        .join(InterviewRounds, Shortlist.profile_id == InterviewRounds.profile_id)
        .join(RoundList, InterviewRounds.round_id == RoundList.id)
        .where(and_(*filters))
        .order_by(asc(order_by_case), Shortlist.created_at.desc())
    )

    res = await db.execute(stmt)
    rows = res.fetchall()
    formatted = []

    for row in rows:
        experience_data = row.resume_data.get("experience", [])
        experience_str = "Fresher"
        if experience_data and isinstance(experience_data, list):
            try:
                yrs = experience_data[0].get("years", 0)
                if yrs:
                    experience_str = f"{yrs} Year{'s' if yrs > 1 else ''} Experience"
            except (IndexError, AttributeError):
                pass

        formatted.append({
            "profile_id": str(row.profile_id),
            "candidate_name": row.candidate_name,
            "experience_level": experience_str,
            "candidate_email": row.candidate_email,
            "overall_score": row.overall_score,
            "result": row.result,
            "round_name": row.round_name,
            "round_status": row.round_status,
            "reason": row.reason,
            "score_breakdown": {
                "Location fit": row.location_score,
                "Potential fit": row.potential_score,
                "Role fit": row.role_fit_score,
                "Skill score": row.skill_score
            },
            "skill_explanation": row.skill_score_explanation or {},
            "extracted_resume_content": row.resume_data,
        })
    return formatted


async def upsert_shortlist_result(
    db: AsyncSession,
    profile_id: str,
    new_result: str,
    reason: str
) -> Shortlist:
    """Update the shortlist record for a given profile_id."""
    valid_results = {"under_review", "shortlist", "reject"}
    if new_result not in valid_results:
        raise ValueError(f"Invalid result '{new_result}'. Must be one of {', '.join(valid_results)}.")

    stmt = select(Shortlist).where(Shortlist.profile_id == profile_id)
    res = await db.execute(stmt)
    shortlist_entry: Optional[Shortlist] = res.scalar_one_or_none()

    if not shortlist_entry:
        raise ValueError(f"No shortlist entry found for profile_id={profile_id}")

    shortlist_entry.result = new_result
    shortlist_entry.reason = reason
    shortlist_entry.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(shortlist_entry)
    return shortlist_entry

