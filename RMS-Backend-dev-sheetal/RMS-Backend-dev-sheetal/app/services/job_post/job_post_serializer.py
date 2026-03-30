# app/services/job_post/job_post_serializer.py

"""Utilities to convert JobDetails ORM instances into API-friendly dictionaries."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db.models.job_post_model import JobDetails

def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Return ISO-8601 string for datetime objects."""
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    try:
        return datetime.fromisoformat(str(dt)).isoformat()
    except Exception:
        return str(dt)


def _collect_locations(job: JobDetails) -> Dict[str, Any]:
    locations_detail: List[Dict[str, Optional[str]]] = []
    location_names: List[str] = []

    for job_location in getattr(job, "locations", []) or []:
        loc_model = getattr(job_location, "location", None)
        location_name = None
        state = None
        country = None

        if loc_model is not None:
            location_name = getattr(loc_model, "location", None)
            state = getattr(loc_model, "state", None)
            country = getattr(loc_model, "country", None)
        else:
            location_name = getattr(job_location, "location", None)

        if location_name:
            location_names.append(location_name)
            locations_detail.append({
                "name": location_name,
                "state": state,
                "country": country,
            })

    primary_location = next((loc for loc in location_names if loc), None)

    def _is_remote(value: Optional[str]) -> bool:
        if not value:
            return False
        lowered = value.strip().lower()
        return lowered in {"work from home", "remote", "wfh"}

    work_from_home = any(_is_remote(name) for name in location_names)

    work_mode = getattr(job, "work_mode", None)
    if isinstance(work_mode, str) and work_mode.lower() in {"remote", "wfh"}:
        work_from_home = True

    return {
        "primary_location": primary_location,
        "locations_detail": locations_detail,
        "location_names": location_names,
        "work_from_home": work_from_home,
        "work_mode": work_mode,
    }


def _serialize_description_sections(job: JobDetails) -> List[Dict[str, str]]:
    sections: List[Dict[str, str]] = []

    for description in getattr(job, "descriptions", []) or []:
        title = getattr(description, "type_description", None) or getattr(description, "title", None) or "Job Description"
        content = getattr(description, "context", None) or getattr(description, "content", None) or ""

        sections.append({
            "title": title,
            "content": content,
            "type_description": title,
            "context": content,
        })

    return sections


def _serialize_skills(job: JobDetails) -> List[Dict[str, Any]]:
    skills: List[Dict[str, Any]] = []
    for job_skill in getattr(job, "job_skills", []) or []:
        skill_model = getattr(job_skill, "skill", None)
        skill_name = getattr(skill_model, "skill_name", None) if skill_model is not None else None
        if not skill_name:
            skill_name = getattr(job_skill, "skill", None)

        skills.append({
            "skill": skill_name,
            "weightage": getattr(job_skill, "weightage", 0) or 0,
        })

    return skills


def _serialize_rounds(job: JobDetails) -> List[Dict[str, Any]]:
    rounds: List[Dict[str, Any]] = []

    for round_item in getattr(job, "rounds", []) or []:
        criteria = None
        evaluation_list = getattr(round_item, "evaluation_criteria", None)
        if evaluation_list:
            criteria = evaluation_list[0]

        rounds.append({
            "level_name": getattr(round_item, "round_name", None),
            "description": getattr(round_item, "round_description", None) or "",
            "round_order": getattr(round_item, "round_order", None) or 0,
            "shortlisting_threshold": getattr(criteria, "shortlisting_criteria", None) if criteria else None,
            "rejected_threshold": getattr(criteria, "rejecting_criteria", None) if criteria else None,
        })

    rounds.sort(key=lambda item: item.get("round_order") or 0)
    return rounds


def serialize_job_details(job: JobDetails) -> Dict[str, Any]:
    """Produce a detailed payload for a single job post."""
    location_info = _collect_locations(job)
    description_sections = _serialize_description_sections(job)
    skills_required = _serialize_skills(job)
    interview_rounds = _serialize_rounds(job)

    job_id = str(getattr(job, "id", "")) if getattr(job, "id", None) else None
    user_id = str(getattr(job, "user_id", "")) if getattr(job, "user_id", None) else None
    creator = getattr(job, "creator", None)
    owner_first_name = getattr(creator, "first_name", None) if creator is not None else None
    owner_last_name = getattr(creator, "last_name", None) if creator is not None else None
    owner_email = getattr(creator, "email", None) if creator is not None else None
    owner_full_name_parts = [part for part in [owner_first_name, owner_last_name] if part]
    owner_full_name = " ".join(owner_full_name_parts) if owner_full_name_parts else None

    return {
        "job_id": job_id,
        "job_title": getattr(job, "job_title", None),
        "job_description": description_sections[0]["content"] if description_sections else None,
        "description_sections": description_sections,
        "skills_required": skills_required,
        "job_location": location_info["primary_location"],
        "job_location_details": location_info["locations_detail"],
        "job_locations": location_info["location_names"],
        "work_mode": location_info["work_mode"],
        "work_from_home": location_info["work_from_home"],
        "minimum_experience": getattr(job, "minimum_experience", None),
        "maximum_experience": getattr(job, "maximum_experience", None),
        "no_of_openings": getattr(job, "no_of_openings", None),
        "rounds_count": getattr(job, "rounds_count", None),
        "is_active": bool(getattr(job, "is_active", False)),
        "active_till": _to_iso(getattr(job, "active_till", None)),
        "posted_date": _to_iso(getattr(job, "posted_date", None)),
        "created_at": _to_iso(getattr(job, "created_at", None)),
        "updated_at": _to_iso(getattr(job, "updated_at", None)),
        "interview_rounds": interview_rounds,
        # Per-round agent configuration (if present)
        "agentRounds": [
            {
                "id": str(ac.id),
                "round_list_id": str(ac.round_list_id) if getattr(ac, 'round_list_id', None) else None,
                "round_name": getattr(ac, 'round_name', None),
                "round_focus": getattr(ac, 'round_focus', None),
                "persona": getattr(ac, 'persona', None),
                "key_skills": getattr(ac, 'key_skills', None) or [],
                "custom_questions": getattr(ac, 'custom_questions', None) or [],
                "forbidden_topics": getattr(ac, 'forbidden_topics', None) or [],
                "interview_mode": getattr(ac, 'interview_mode', None),
                "interview_time_min": getattr(ac, 'interview_time_min', None),
                "interview_time_max": getattr(ac, 'interview_time_max', None),
                "interviewer_id": str(getattr(ac, 'interviewer_id')) if getattr(ac, 'interviewer_id', None) else None,
                "coding_enabled": bool(getattr(ac, 'coding_enabled', False)),
                "coding_question_mode": getattr(ac, 'coding_question_mode', 'ai'),
                "coding_difficulty": getattr(ac, 'coding_difficulty', 'medium'),
                "coding_languages": getattr(ac, 'coding_languages', None) or ["python"],
                "provided_coding_question": getattr(ac, 'provided_coding_question', None),
                "coding_test_case_mode": getattr(ac, 'coding_test_case_mode', 'provided'),
                "coding_test_cases": getattr(ac, 'coding_test_cases', None) or [],
                "coding_starter_code": getattr(ac, 'coding_starter_code', None) or {},
                "mcq_enabled": bool(getattr(ac, 'mcq_enabled', False)),
                "mcq_question_mode": getattr(ac, 'mcq_question_mode', 'provided'),
                "mcq_difficulty": getattr(ac, 'mcq_difficulty', 'medium'),
                "mcq_questions": getattr(ac, 'mcq_questions', None) or [],
                "mcq_passing_score": getattr(ac, 'mcq_passing_score', 60),
            }
            for ac in (getattr(job, 'agent_configs', []) or [])
        ],
        "role_fit": getattr(job, "role_fit", None),
        "potential_fit": getattr(job, "potential_fit", None),
        "location_fit": getattr(job, "location_fit", None),
        "career_activation_mode": getattr(job, "career_activation_mode", None),
        "career_activation_days": getattr(job, "career_activation_days", None),
        "career_shortlist_threshold": getattr(job, "career_shortlist_threshold", None),
        "total_candidates": getattr(job, "total_candidates", 0) or 0,
        "shortlisted_count": getattr(job, "shortlisted_count", 0) or 0,
        "under_review_count": getattr(job, "under_review_count", 0) or 0,
        "rejected_count": getattr(job, "rejected_count", 0) or 0,
        "user_id": user_id,
        "created_by_user_id": user_id,
        "author_id": user_id,
        "owner_first_name": owner_first_name,
        "owner_last_name": owner_last_name,
        "owner_name": owner_full_name,
        "owner_email": owner_email,
        "creator": {
            "user_id": user_id,
            "first_name": owner_first_name,
            "last_name": owner_last_name,
            "email": owner_email,
            "full_name": owner_full_name,
        } if creator is not None else None,
    }


def serialize_admin_job(job: JobDetails) -> Dict[str, Any]:
    """Compact representation for internal job listings with full details."""
    details = serialize_job_details(job)
    job_id = details["job_id"]
    user_id = details["user_id"]

    return {
        "job_id": job_id,
        "id": job_id,
        "jobId": job_id,
        "job_title": details["job_title"],
        "job_description": details["job_description"],
        "description_sections": details["description_sections"],
        "job_location": details["job_location"],
        "job_location_details": details["job_location_details"],
        "job_locations": details["job_locations"],
        "work_mode": details["work_mode"],
        "work_from_home": details["work_from_home"],
        "minimum_experience": details["minimum_experience"],
        "maximum_experience": details["maximum_experience"],
        "no_of_openings": details["no_of_openings"],
        "rounds_count": details["rounds_count"],
        "skills_required": details["skills_required"],
        "interview_rounds": details["interview_rounds"],
        "agentRounds": details.get("agentRounds", []),
        "role_fit": details["role_fit"],
        "potential_fit": details["potential_fit"],
        "location_fit": details["location_fit"],
        "career_activation_mode": details["career_activation_mode"],
        "career_activation_days": details["career_activation_days"],
        "career_shortlist_threshold": details["career_shortlist_threshold"],
        "created_by_user_id": user_id,
        "user_id": user_id,
        "author_id": user_id,
        "is_active": details["is_active"],
        "active_till": details["active_till"],
        "posted_date": details["posted_date"],
        "created_at": details["created_at"],
        "updated_at": details["updated_at"],
        "shortlisting_criteria": details.get("career_shortlist_threshold") or 0,
        "rejection_criteria": 0,
        "profile_counts": {
            "applied": details.get("total_candidates", 0) or 0,
            "shortlisted": details.get("shortlisted_count", 0) or 0,
            "rejected": details.get("rejected_count", 0) or 0,
            "under_review": details.get("under_review_count", 0) or 0,
        },
        "total_candidates": details.get("total_candidates", 0) or 0,
        "shortlisted_count": details.get("shortlisted_count", 0) or 0,
        "under_review_count": details.get("under_review_count", 0) or 0,
        "rejected_count": details.get("rejected_count", 0) or 0,
        "is_pinned": False,
        "can_edit": False,  # Will be set by controller based on user permissions
        "owner_name": details.get("owner_name"),
        "owner_email": details.get("owner_email"),
        "owner_first_name": details.get("owner_first_name"),
        "owner_last_name": details.get("owner_last_name"),
        "creator": details.get("creator"),
    }


def serialize_public_job(job: JobDetails) -> Dict[str, Any]:
    """Public-friendly payload for career site listings."""
    details = serialize_job_details(job)
    job_id = details["job_id"]
    user_id = details["user_id"]

    return {
        "job_id": job_id,
        "id": job_id,
        "jobId": job_id,
        "job_title": details["job_title"],
        "job_description": details["job_description"],
        "job_location": details["job_location"],
        "minimum_experience": details["minimum_experience"],
        "maximum_experience": details["maximum_experience"],
        "skills_required": details["skills_required"],
        "is_active": details["is_active"],
        "posted_date": details["posted_date"],
        "created_by_user_id": user_id,
        "user_id": user_id,
    }


class JobPostSerializer:
    """Compatibility wrapper providing the class API expected by older modules.

    New code should call the plain functions (e.g., serialize_public_job), but
    some services expect a `JobPostSerializer` class with helper methods. This
    adapter keeps backward compatibility.
    """

    @staticmethod
    def format_job_details_orm(job: JobDetails) -> Dict[str, Any]:
        """Format ORM JobDetails for public-facing listings."""
        return serialize_public_job(job)

    @staticmethod
    def format_admin_job_orm(job: JobDetails) -> Dict[str, Any]:
        """Format ORM JobDetails for admin/internal listings."""
        return serialize_admin_job(job)

    @staticmethod
    def format_full_job_orm(job: JobDetails) -> Dict[str, Any]:
        """Full detailed job serialization."""
        return serialize_job_details(job)
