# app/db/repository/job_post_repository.py

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy import select, update, insert, delete, or_, case, text, func, distinct

from app.db.models.curation_model import Curation
from app.db.models.shortlist_model import Shortlist
from app.db.models.resume_model import InterviewRounds, Profile
from app.db.models.job_post_model import (
    JobDetails,
    JobSkills,
    SkillList,
    JobDescription,
    JobLocations,
    LocationList,
    RoundList,
    EvaluationCriteria,
)
from app.db.models.agent_config_model import AgentRoundConfig # Import new model

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# EAGER LOAD OPTIONS
# -------------------------------------------------------
def _job_details_load_options():
    """
    Lazily construct eager load options. In some test environments the
    ORM instrumentation may not be available at import time, so building
    these options can fail. Return an empty list in that case.
    """
    try:
        return [
            selectinload(JobDetails.job_skills).selectinload(JobSkills.skill),
            selectinload(JobDetails.descriptions),
            selectinload(JobDetails.locations).selectinload(JobLocations.location),
            selectinload(JobDetails.rounds).selectinload(RoundList.evaluation_criteria),
            selectinload(JobDetails.creator),
        ]
    except Exception:
        return []


# Using a function above ensures ORM instrumentation issues during import are handled.
JOB_DETAILS_LOAD_OPTIONS = _job_details_load_options()


def _posted_date_desc():
    """
    Helper to safely get a 'desc' expression for JobDetails.posted_date.
    In unit test environments, JobDetails.posted_date may be a SimpleNamespace
    without a 'desc' method; fall back to returning the bare attribute.
    """
    posted = getattr(JobDetails, "posted_date", None)
    if posted is None:
        return posted
    try:
        return posted.desc()
    except Exception:
        return posted


# -------------------------------------------------------
# AUTOCOMPLETE SUGGESTIONS
# -------------------------------------------------------
async def get_search_autocomplete_suggestions(db: AsyncSession) -> Dict[str, List[str]]:
    """
    Fetches all unique, non-empty job titles, skill names and location names
    to power the career page search boxes.
    """
    try:
        # Fetch job titles
        job_title_stmt = select(JobDetails.job_title).where(
            JobDetails.job_title.is_not(None), 
            JobDetails.job_title != '',
            JobDetails.is_active == True
        ).distinct()
        job_title_res = await db.execute(job_title_stmt)
        job_titles = [row[0] for row in job_title_res.all()]
        
        # Fetch skills
        skill_stmt = select(SkillList.skill_name).where(SkillList.skill_name.is_not(None), SkillList.skill_name != '').distinct()
        skill_res = await db.execute(skill_stmt)
        skills = [row[0] for row in skill_res.all()]
        
        # Fetch locations
        loc_stmt = select(LocationList.location).where(LocationList.location.is_not(None), LocationList.location != '').distinct()
        loc_res = await db.execute(loc_stmt)
        locations = [row[0] for row in loc_res.all()]

        return {
            "job_titles": job_titles,
            "skills": skills,
            "locations": locations
        }
    except Exception as e:
        logger.error(f"[JobRepo] get_search_autocomplete_suggestions failed: {e}")
        return {"job_titles": [], "skills": [], "locations": []}


# -------------------------------------------------------
# RANKED PUBLIC JOB SEARCH
# -------------------------------------------------------
async def search_active_job_details(
    db: AsyncSession,
    search_role: Optional[str],
    search_skills: List[str],
    search_locations: List[str]
) -> List[Tuple[JobDetails, int]]:
    """
    Performs a weighted search for active job posts.
    
    Returns a list of tuples: (JobDetails, score)
    """
    
    # Define weights for scoring
    ROLE_WEIGHT = 5      # High weight for a direct title match
    SKILL_WEIGHT = 3     # Medium weight for each matching skill
    LOCATION_WEIGHT = 2  # Medium weight for each matching location
    
    # --- 1. Define aliases for our joins ---
    # This is crucial for OUTER JOINs to work correctly in aggregations
    job_skills_alias = aliased(JobSkills)
    skill_list_alias = aliased(SkillList)
    job_locations_alias = aliased(JobLocations)
    location_list_alias = aliased(LocationList)
    
    # --- 2. Build the scoring logic ---
    
    # Role Score: 5 points if it matches, 0 otherwise.
    # We use ILIKE for case-insensitive partial matching.
    role_score = case(
        (JobDetails.job_title.ilike(f"%{search_role}%"), ROLE_WEIGHT),
        else_=0
    ) if search_role else 0 # If no role query, score is 0
    
    # Skill Score: 3 points for *each* skill that matches the user's query list.
    # We use func.count(distinct case(...)) to count matching skills.
    skill_matches = func.count(distinct(
        case(
            (skill_list_alias.skill_name.in_(search_skills), skill_list_alias.id),
            else_=None
        )
    ))
    skill_score = skill_matches * SKILL_WEIGHT
    
    # Location Score: 2 points for *each* location that matches.
    location_matches = func.count(distinct(
        case(
            (location_list_alias.location.in_(search_locations), location_list_alias.id),
            else_=None
        )
    ))

    remote_bonus = case(
        (
            (JobDetails.work_mode.in_(['remote', 'hybrid', 'wfh'])) & 
            (len(search_locations) > 0),
            len(search_locations) 
        ),
        else_=0
    ) if search_locations else 0
    
    location_score = (location_matches + remote_bonus) * LOCATION_WEIGHT

    # --- 3. Combine scores into a total ---
    total_score = (role_score + skill_score + location_score).label("total_score")

    # --- 4. Build the main query ---
    stmt = (
        select(
            JobDetails,
            total_score
        )
        .select_from(JobDetails)
        # Use OUTER JOINs so we don't exclude jobs that have no skills/locations
        .outerjoin(job_skills_alias, JobDetails.id == job_skills_alias.job_id)
        .outerjoin(skill_list_alias, job_skills_alias.skill_id == skill_list_alias.id)
        .outerjoin(job_locations_alias, JobDetails.id == job_locations_alias.job_id)
        .outerjoin(location_list_alias, job_locations_alias.location_id == location_list_alias.id)
        # --- 5. Apply Filters ---
        .where(
            JobDetails.is_active == True
        )
        # --- 6. Group by Job ID to aggregate scores ---
        .group_by(JobDetails.id)
        # --- 7. Filter out non-matches ---
        # HAVING is like WHERE, but for aggregated fields (like our total_score)
        # We only want jobs that matched *something*.
        .having(
            total_score > 0
        )
        # --- 8. Order by score (descending) and then by date ---
        .order_by(
            total_score.desc(),
            _posted_date_desc()
        )
    # --- 9. Apply eager loading ---
    .options(*_job_details_load_options())
    )

    try:
        res = await db.execute(stmt)
        # This will return a list of Row objects, e.g., [(JobDetails_ORM_1, 10), (JobDetails_ORM_2, 8)]
        results: List[Tuple[JobDetails, int]] = res.all()
        return results
    except Exception as e:
        logger.error(f"[JobRepo] search_active_job_details failed: {e}", exc_info=True)
        raise

# -------------------------------------------------------
# CREATE / UPDATE JOB DETAILS
# -------------------------------------------------------
async def update_or_create_job_details(
    db: AsyncSession,
    job_id: Optional[str],
    job_data: Dict[str, Any],
    skills_data: List[Dict[str, Any]] = None,
    description_data: List[Dict[str, Any]] = None,
    location_data: List[Dict[str, Any]] = None,
    rounds_data: List[Dict[str, Any]] = None,
    agent_configs_data: List[Dict[str, Any]] = None,
) -> JobDetails:
    """Create or update a job post with related entities."""

    try:
        if job_id:
            job_uuid = uuid.UUID(job_id)
            result = await db.execute(select(JobDetails).where(JobDetails.id == job_uuid))
            job = result.scalar_one_or_none()
        else:
            job_uuid = uuid.uuid4()
            job = None

        timestamp = datetime.now(timezone.utc)
        raw_job_data = dict(job_data or {})
        raw_job_data = dict(job_data or {})
        if 'min_salary' in raw_job_data and 'minimum_salary' not in raw_job_data:
            raw_job_data['minimum_salary'] = raw_job_data.pop('min_salary')
        if 'max_salary' in raw_job_data and 'maximum_salary' not in raw_job_data:
            raw_job_data['maximum_salary'] = raw_job_data.pop('max_salary')
        # camelCase variants
        if 'minimumSalary' in raw_job_data and 'minimum_salary' not in raw_job_data:
            raw_job_data['minimum_salary'] = raw_job_data.pop('minimumSalary')
        if 'maximumSalary' in raw_job_data and 'maximum_salary' not in raw_job_data:
            raw_job_data['maximum_salary'] = raw_job_data.pop('maximumSalary')

        # Normalize salary values: empty strings or falsy values -> None; numeric strings -> int
        for _sal_key in ('minimum_salary', 'maximum_salary'):
            if _sal_key in raw_job_data:
                sval = raw_job_data.get(_sal_key)
                if sval is None or (isinstance(sval, str) and str(sval).strip() == ''):
                    raw_job_data[_sal_key] = None
                else:
                    try:
                        # Accept numbers or numeric strings
                        raw_job_data[_sal_key] = int(sval)
                    except Exception:
                        try:
                            raw_job_data[_sal_key] = int(float(str(sval).replace(',', '').strip()))
                        except Exception:
                            # Leave as-is (DB layer will raise if incompatible)
                            pass

        allowed_columns = {c.name for c in JobDetails.__table__.columns}
        job_data = {k: v for k, v in raw_job_data.items() if k in allowed_columns}

        # If rounds_data is provided in this request, persist the total
        # rounds count into the job_data so JobDetails.rounds_count is kept
        # in sync with the inserted/updated RoundList rows.
        try:
            if rounds_data is not None:
                # rounds_data may be a list (or None). Count entries if list-like.
                try:
                    job_data['rounds_count'] = int(len(rounds_data))
                except Exception:
                    # Best-effort: if rounds_data not list-like, leave as-is
                    pass
        except Exception:
            # Non-fatal: continue without setting rounds_count
            pass

        # ---------------------------------------
        # UPSERT core job record
        # ---------------------------------------

        user_id_to_check = job_data.get("user_id")

        if job:
            logger.info(f"[JobRepo] Updating job with id={job_uuid}")
            # Remove immutable fields that should not be overridden during update
            for auto_field in ("id", "created_at", "updated_at", "posted_date"):
                job_data.pop(auto_field, None)

            print(f"[DEBUG REPO] About to update job {job_uuid} with data:")
            for key, value in job_data.items():
                print(f"  - {key}: {value}")

            result = await db.execute(
                update(JobDetails)
                .where(JobDetails.id == job_uuid)
                .values(**job_data, updated_at=timestamp)
            )
            
            print(f"[DEBUG REPO] Update query executed. Rows affected: {result.rowcount}")
            if result.rowcount == 0:
                print(f"[WARNING REPO] No rows were updated for job_id: {job_uuid}")
            else:
                print(f"[DEBUG REPO] Successfully updated {result.rowcount} row(s)")

            # Delete related entities for clean re-insert **only if** new data is provided.
            # This prevents accidental loss when update payload omits optional sections.
            if skills_data is not None:
                await db.execute(delete(JobSkills).where(JobSkills.job_id == job_uuid))
            if description_data is not None:
                await db.execute(delete(JobDescription).where(JobDescription.job_id == job_uuid))
            if location_data is not None:
                await db.execute(delete(JobLocations).where(JobLocations.job_id == job_uuid))
            if rounds_data is not None:
                # CRITICAL FIX: Delete evaluation_criteria BEFORE deleting round_list to avoid FK constraint violation
                print(f"[DEBUG REPO] Deleting evaluation_criteria before rounds for job {job_uuid}")
                await db.execute(delete(EvaluationCriteria).where(EvaluationCriteria.job_id == job_uuid))
                # Also delete any interview_rounds that reference these rounds (child records from profiles)
                # This prevents foreign key violations when removing round_list entries.
                try:
                    print(f"[DEBUG REPO] Deleting interview_rounds for job {job_uuid} before removing rounds")
                    await db.execute(delete(InterviewRounds).where(InterviewRounds.job_id == job_uuid))
                except Exception:
                    # If InterviewRounds model or table isn't present in some test environments,
                    # ignore and proceed to delete round_list. The hard-delete path handles full cleanup.
                    print(f"[WARN REPO] Could not delete InterviewRounds for job {job_uuid} (may not exist in this env)")
                # If agent configs data provided, delete existing agent configs first
                if agent_configs_data is not None:
                    try:
                        print(f"[DEBUG REPO] Deleting existing round_config for job {job_uuid}")
                        await db.execute(delete(AgentRoundConfig).where(AgentRoundConfig.job_id == job_uuid))
                    except Exception:
                        print(f"[WARN REPO] Could not delete round_config for job {job_uuid}")

                print(f"[DEBUG REPO] Deleting round_list for job {job_uuid}")
                await db.execute(delete(RoundList).where(RoundList.job_id == job_uuid))
        else:
            logger.info(f"[JobRepo] Inserting new job with id={job_uuid}")
            if not user_id_to_check:
                # This should be prevented earlier, but double-check here.
                raise ValueError("Missing user_id for job creation.")

            # Run a lightweight existence check against the users table.
            user_exists_stmt = text("SELECT 1 FROM users WHERE user_id = :uid")
            user_res = await db.execute(user_exists_stmt, {"uid": str(user_id_to_check)})
            user_row = user_res.first()
            if not user_row:
                # Raise a clear exception to be handled by service/controller
                raise ValueError(f"Creator user_id '{user_id_to_check}' does not exist in users table.")

            for auto_field in ("id", "created_at", "updated_at"):
                job_data.pop(auto_field, None)

            posted_date = job_data.pop("posted_date", timestamp)

            await db.execute(
                insert(JobDetails).values(
                    id=job_uuid,
                    created_at=timestamp,
                    updated_at=timestamp,
                    posted_date=posted_date,
                    **job_data,
                )
            )

        # ---------------------------------------
        # INSERT SKILLS
        # ---------------------------------------
        if skills_data:
            for s in skills_data:
                skill_name = s.get("skill_name")
                weightage = s.get("weightage", 0)

                # Ensure skill exists in SkillList
                skill_row = await db.execute(select(SkillList).where(SkillList.skill_name == skill_name))
                skill = skill_row.scalar_one_or_none()
                if not skill:
                    skill_id = uuid.uuid4()
                    await db.execute(insert(SkillList).values(id=skill_id, skill_name=skill_name))
                else:
                    skill_id = skill.id

                await db.execute(
                    insert(JobSkills).values(
                        id=uuid.uuid4(),
                        job_id=job_uuid,
                        skill_id=skill_id,
                        weightage=weightage,
                    )
                )

        # ---------------------------------------
        # INSERT DESCRIPTIONS
        # ---------------------------------------
        if description_data:
            for d in description_data:
                await db.execute(
                    insert(JobDescription).values(
                        id=uuid.uuid4(),
                        job_id=job_uuid,
                        type_description=d.get("type_description"),
                        context=d.get("context"),
                        created_at=timestamp,
                    )
                )

        # ---------------------------------------
        # INSERT LOCATIONS
        # ---------------------------------------
        if location_data:
            for loc in location_data:
                location_name = loc.get("location")
                loc_query = await db.execute(select(LocationList).where(LocationList.location == location_name))
                location = loc_query.scalar_one_or_none()

                if not location:
                    loc_id = uuid.uuid4()
                    await db.execute(
                        insert(LocationList).values(
                            id=loc_id,
                            location=location_name,
                            state=loc.get("state"),
                            country=loc.get("country"),
                        )
                    )
                else:
                    loc_id = location.id

                await db.execute(
                    insert(JobLocations).values(
                        id=uuid.uuid4(),
                        job_id=job_uuid,
                        location_id=loc_id,
                    )
                )

        # ---------------------------------------
        # INSERT ROUNDS & EVALUATION CRITERIA
        # Track created round IDs so agent-configs can reference them
        # ---------------------------------------
        round_map_by_order = {}
        round_map_by_name = {}
        # Map evaluation thresholds captured during round insertion
        round_thresholds_by_order = {}
        round_thresholds_by_name = {}
        round_thresholds_by_id = {}
        if rounds_data:
            for r in rounds_data:
                round_id = uuid.uuid4()
                round_order = r.get("round_order")
                round_name = r.get("round_name")

                await db.execute(
                    insert(RoundList).values(
                        id=round_id,
                        job_id=job_uuid,
                        round_name=round_name,
                        round_description=r.get("round_description"),
                        round_order=round_order,
                    )
                )

                # Save mapping by order and name for later agent-config linking
                if round_order is not None:
                    round_map_by_order[int(round_order)] = round_id
                if round_name:
                    round_map_by_name[str(round_name).strip()] = round_id

                eval_data = r.get("evaluation_criteria")
                if eval_data:
                    await db.execute(
                        insert(EvaluationCriteria).values(
                            id=uuid.uuid4(),
                            round_id=round_id,
                            job_id=job_uuid,
                            shortlisting_criteria=eval_data.get("shortlisting_criteria", 60),
                            rejecting_criteria=eval_data.get("rejecting_criteria", 40),
                        )
                    )
                    # Record thresholds for later use when creating AgentRoundConfig
                    try:
                        short_th = eval_data.get("shortlisting_criteria")
                        rej_th = eval_data.get("rejecting_criteria")
                        if round_order is not None:
                            round_thresholds_by_order[int(round_order)] = {
                                'shortlisting': short_th,
                                'rejecting': rej_th,
                            }
                        if round_name:
                            round_thresholds_by_name[str(round_name).strip()] = {
                                'shortlisting': short_th,
                                'rejecting': rej_th,
                            }
                        round_thresholds_by_id[round_id] = {
                            'shortlisting': short_th,
                            'rejecting': rej_th,
                        }
                    except Exception:
                        pass

        # ---------------------------------------
        # INSERT AGENT CONFIGS (per-round)
        # Resolve round_list_id from created rounds (by id, order, or name).
        # Enforce persona=null for offline/in-person modes and persist
        # any provided score_distribution.
        # ---------------------------------------
        if agent_configs_data:
            for ac in agent_configs_data:
                # Resolve round_list_id
                resolved_round_id = None
                candidate = ac.get('roundListId') or ac.get('round_list_id')
                if candidate:
                    # candidate may be a UUID string or an integer index or name
                    # Prefer the round IDs created during this update (round_map_by_order/name).
                    # If the candidate is a UUID, only accept it if it exists for this job
                    # (this avoids using stale UUIDs that were deleted above).
                    try:
                        # Try UUID first
                        cand_uuid = uuid.UUID(str(candidate))
                        # If this UUID matches one of the newly created rounds, accept it.
                        if cand_uuid in set(round_map_by_order.values()) or cand_uuid in set(round_map_by_name.values()):
                            resolved_round_id = cand_uuid
                        else:
                            # Otherwise, check DB to see if this UUID exists and belongs to this job.
                            try:
                                row = await db.execute(select(RoundList).where(RoundList.id == cand_uuid, RoundList.job_id == job_uuid))
                                existing_round = row.scalar_one_or_none()
                                if existing_round:
                                    resolved_round_id = cand_uuid
                                else:
                                    resolved_round_id = None
                            except Exception:
                                resolved_round_id = None
                    except Exception:
                        # Not a UUID — try by order (int)
                        try:
                            idx = int(candidate)
                            resolved_round_id = round_map_by_order.get(idx)
                        except Exception:
                            # Try by name
                            resolved_round_id = round_map_by_name.get(str(candidate).strip())

                # If still not found, try matching by round name provided in ac
                if not resolved_round_id:
                    name_candidate = ac.get('roundName') or ac.get('round_name')
                    if name_candidate:
                        resolved_round_id = round_map_by_name.get(str(name_candidate).strip())

                # Also allow matching by round order field
                if not resolved_round_id and ac.get('round_order') is not None:
                    try:
                        resolved_round_id = round_map_by_order.get(int(ac.get('round_order')))
                    except Exception:
                        resolved_round_id = None

                interview_mode = (ac.get('interview_mode') or ac.get('interviewMode') or 'agent').lower()

                # persona should be NULL for offline/in-person modes
                offline_modes = {'offline', 'in_person', 'inperson', 'in-person', 'in person'}
                if interview_mode in offline_modes:
                    persona_val = None
                else:
                    persona_val = ac.get('persona') if ac.get('persona') is not None else ac.get('persona', 'alex')

                # score distribution: accept snake/camel keys or fallback to None
                score_dist = ac.get('score_distribution') or ac.get('scoreDistribution') or None

                # If frontend did not provide a score_distribution, attempt to
                # build one from available metrics and evaluation criteria so every
                # round can optionally store shortlisting/rejecting thresholds
                # inside the score_distribution JSONB.
                try:
                    if not score_dist:
                        score_dist = {}

                    # Add any direct metrics provided on agent-config payload
                    role_val = ac.get('role_fit') or ac.get('roleFit') or ac.get('role') or None
                    potential_val = ac.get('potential_fit') or ac.get('potentialFit') or ac.get('potential') or None
                    location_val = ac.get('location_fit') or ac.get('locationFit') or ac.get('location') or None

                    if role_val is not None:
                        try:
                            score_dist['role_fit'] = int(role_val)
                        except Exception:
                            score_dist['role_fit'] = role_val
                    if potential_val is not None:
                        try:
                            score_dist['potential'] = int(potential_val)
                        except Exception:
                            score_dist['potential'] = potential_val
                    if location_val is not None:
                        try:
                            score_dist['location'] = int(location_val)
                        except Exception:
                            score_dist['location'] = location_val

                    # Include shortlisting/rejecting thresholds either from the agent-config
                    # payload or from the evaluation criteria captured when rounds were created.
                    short_th = ac.get('shortlisting_threshold') or ac.get('shortlistingThreshold') or ac.get('shortlisting') or None
                    rej_th = ac.get('rejecting_threshold') or ac.get('rejectingThreshold') or ac.get('rejecting') or None

                    if short_th is None or rej_th is None:
                        # Try by resolved_round_id using thresholds we captured during this request
                        if resolved_round_id and resolved_round_id in round_thresholds_by_id:
                            found = round_thresholds_by_id.get(resolved_round_id)
                            if found:
                                if short_th is None:
                                    short_th = found.get('shortlisting')
                                if rej_th is None:
                                    rej_th = found.get('rejecting')

                        # If still missing and we have a resolved_round_id, try fetching existing
                        # EvaluationCriteria from the DB (covers rounds created earlier).
                        if (short_th is None or rej_th is None) and resolved_round_id:
                            try:
                                row = await db.execute(
                                    select(EvaluationCriteria).where(
                                        EvaluationCriteria.round_id == resolved_round_id,
                                        EvaluationCriteria.job_id == job_uuid
                                    )
                                )
                                existing_eval = row.scalar_one_or_none()
                                if existing_eval:
                                    if short_th is None:
                                        short_th = existing_eval.shortlisting_criteria
                                    if rej_th is None:
                                        rej_th = existing_eval.rejecting_criteria
                            except Exception:
                                # best-effort: ignore DB errors here and continue
                                pass
                        # Try by order
                        if (short_th is None or rej_th is None) and ac.get('round_order') is not None:
                            try:
                                fr = round_thresholds_by_order.get(int(ac.get('round_order')))
                                if fr:
                                    if short_th is None:
                                        short_th = fr.get('shortlisting')
                                    if rej_th is None:
                                        rej_th = fr.get('rejecting')
                            except Exception:
                                pass
                        # Try by round name
                        if (short_th is None or rej_th is None):
                            rn = ac.get('roundName') or ac.get('round_name')
                            if rn:
                                fr = round_thresholds_by_name.get(str(rn).strip())
                                if fr:
                                    if short_th is None:
                                        short_th = fr.get('shortlisting')
                                    if rej_th is None:
                                        rej_th = fr.get('rejecting')

                    if short_th is not None:
                        try:
                            score_dist['shortlisting'] = int(short_th)
                        except Exception:
                            score_dist['shortlisting'] = short_th
                    if rej_th is not None:
                        try:
                            score_dist['rejecting'] = int(rej_th)
                        except Exception:
                            score_dist['rejecting'] = rej_th

                    # If the constructed score_dist remains empty, set to None
                    if not score_dist:
                        score_dist = None
                except Exception:
                    # Best-effort: fallback to whatever was provided
                    pass

                await db.execute(
                    insert(AgentRoundConfig).values(
                        id=uuid.uuid4(),
                        job_id=job_uuid,
                        round_list_id=resolved_round_id,
                        round_name=ac.get('roundName') or ac.get('round_name') or None,
                        round_focus=ac.get('roundFocus') or ac.get('round_focus'),
                        persona=persona_val,
                        key_skills=ac.get('keySkills') or ac.get('key_skills') or [],
                        custom_questions=ac.get('customQuestions') or ac.get('custom_questions') or [],
                        forbidden_topics=ac.get('forbiddenTopics') or ac.get('forbidden_topics') or [],
                        interview_mode=interview_mode,
                        interview_time_min=ac.get('interview_time_min') or ac.get('interviewTimeMin') or ac.get('interview_time') or ac.get('interviewTime'),
                        interview_time_max=ac.get('interview_time_max') or ac.get('interviewTimeMax') or ac.get('interview_time') or ac.get('interviewTime'),
                        interviewer_id=ac.get('interviewer_id') or ac.get('interviewerId'),
                        score_distribution=score_dist,
                    )
                )

        await db.commit()

        # ---------------------------------------
        # Fetch final job record with eager loads
        # ---------------------------------------
        res = await db.execute(
            select(JobDetails)
            .where(JobDetails.id == job_uuid)
            .options(*JOB_DETAILS_LOAD_OPTIONS)
        )
        return res.scalar_one_or_none()

    except Exception as e:
        await db.rollback()
        logger.error(f"[JobRepo] update_or_create_job_details failed: {e}")
        raise


# -------------------------------------------------------
# GET JOB BY ID
# -------------------------------------------------------
async def get_job_details_by_id(db: AsyncSession, job_id: str) -> Optional[JobDetails]:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        # OPTIMIZED: Return None immediately on invalid UUID.
        return None

    stmt = select(JobDetails).where(JobDetails.id == job_uuid).options(*JOB_DETAILS_LOAD_OPTIONS)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


# -------------------------------------------------------
# LIST / ACTIVE JOB HELPERS
# -------------------------------------------------------
async def get_all_job_details(db: AsyncSession) -> List[JobDetails]:
    """Return all job posts with eager-loaded relations."""
    try:
        stmt = select(JobDetails).options(*JOB_DETAILS_LOAD_OPTIONS)
        order_col = _posted_date_desc()
        if order_col is not None:
            stmt = stmt.order_by(order_col)
        res = await db.execute(stmt)
        rows = res.scalars().all()
        return rows
    except Exception as e:
        logger.error(f"[JobRepo] get_all_job_details failed: {e}")
        raise


async def get_active_job_details(db: AsyncSession) -> List[JobDetails]:
    """Return only active job posts (is_active=True)."""
    try:
        stmt = select(JobDetails).where(JobDetails.is_active == True).options(*JOB_DETAILS_LOAD_OPTIONS)
        order_col = _posted_date_desc()
        if order_col is not None:
            stmt = stmt.order_by(order_col)
        res = await db.execute(stmt)
        rows = res.scalars().all()
        return rows
    except Exception as e:
        logger.error(f"[JobRepo] get_active_job_details failed: {e}")
        raise

# -------------------------------------------------------
# CHECK JOB_ID EXISTENCE FOR RESUME UPLOAD
# -------------------------------------------------------

async def job_exists(db: AsyncSession, job_id: str) -> bool:
    """Check if a job_id exists in job_details table."""
    try:
        if db is None:
            logger.error(f"[JobRepo] job_exists called with None db for job_id={job_id}")
            return False
        result = await db.execute(
            select(JobDetails.id).where(JobDetails.id == uuid.UUID(job_id))
        )
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"[JobRepo] job_exists check failed for job_id={job_id}: {e}")
        # On any error (including invalid UUID or DB issues), return False to indicate job not found
        return False

async def get_jobs_by_user_id(db: AsyncSession, user_id: str) -> List[JobDetails]:
    """Return all job posts created by a specific user."""
    try:
        stmt = (
            select(JobDetails)
            .where(JobDetails.user_id == user_id)
            .options(*JOB_DETAILS_LOAD_OPTIONS)
        )
        order_col = _posted_date_desc()
        if order_col is not None:
            stmt = stmt.order_by(order_col)
        res = await db.execute(stmt)
        rows = res.scalars().all()
        return rows
    except Exception as e:
        logger.error(f"[JobRepo] get_jobs_by_user_id failed: {e}")
        raise

async def get_agent_jobs_by_user_id(db: AsyncSession, user_id: str) -> List[JobDetails]:
    """Return all job posts created by a specific user that have is_agent_interview = True."""
    try:
        stmt = (
            select(JobDetails)
            .where(
                JobDetails.user_id == user_id,
                JobDetails.is_agent_interview == True
            )
            .options(
                *JOB_DETAILS_LOAD_OPTIONS,
                selectinload(JobDetails.agent_configs)
            )
        )
        order_col = _posted_date_desc()
        if order_col is not None:
            stmt = stmt.order_by(order_col)
        res = await db.execute(stmt)
        rows = res.scalars().all()
        return rows
    except Exception as e:
        logger.error(f"[JobRepo] get_agent_jobs_by_user_id failed: {e}")
        raise
# -------------------------------------------------------
# STATUS / SOFT DELETE HELPERS
# -------------------------------------------------------
async def set_job_active_status(db: AsyncSession, job_id: str, is_active: bool) -> Optional[JobDetails]:
    """Set the is_active flag for a job and return the updated job record."""
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        return None

    try:
        timestamp = datetime.now(timezone.utc)
        await db.execute(
            update(JobDetails).where(JobDetails.id == job_uuid).values(is_active=is_active, updated_at=timestamp)
        )
        await db.commit()

        # Return fresh job
        return await get_job_details_by_id(db, job_id)
    except Exception as e:
        await db.rollback()
        logger.error(f"[JobRepo] set_job_active_status failed: {e}")
        raise


async def soft_delete_job_by_id(db: AsyncSession, job_id: str) -> bool:
    """Soft-delete a job (mark is_active False). Returns True if deleted."""
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        logger.error(f"[JobRepo] soft_delete_job_by_id: Invalid UUID format for {job_id}")
        return False

    try:
        result = await db.execute(
            update(JobDetails)
            .where(JobDetails.id == job_uuid)
            .values(is_active=False)
        )
        rows_affected = result.rowcount
        logger.info(f"[JobRepo] soft_delete_job_by_id: Updated {rows_affected} row(s) for job_id={job_id}")
        
        if rows_affected == 0:
            logger.warning(f"[JobRepo] soft_delete_job_by_id: No job found with id={job_id}")
            await db.commit()
            return False
        
        await db.commit()
        logger.info(f"[JobRepo] soft_delete_job_by_id: Successfully soft-deleted job_id={job_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"[JobRepo] soft_delete_job_by_id failed: {e}")
        raise


async def soft_delete_jobs_batch(db: AsyncSession, job_ids: List[str]) -> int:
    """Soft-delete multiple jobs. Returns number of rows affected."""
    uuids = []
    for jid in job_ids:
        try:
            uuids.append(uuid.UUID(jid))
        except Exception:
            continue
    if not uuids:
        return 0

    try:
        res = await db.execute(update(JobDetails).where(JobDetails.id.in_(uuids)).values(is_active=False))
        await db.commit()
        return res.rowcount
    except Exception as e:
        await db.rollback()
        logger.error(f"[JobRepo] soft_delete_jobs_batch failed: {e}")
        raise


async def hard_delete_job_by_id(db: AsyncSession, job_id: str) -> bool:
    """
    Permanently delete a job post and all related records from the database.
    This is a HARD DELETE - the data cannot be recovered.
    Returns True if deleted successfully.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        logger.error(f"[JobRepo] hard_delete_job_by_id: Invalid UUID format for {job_id}")
        return False

    try:
        # Delete related records first to avoid foreign key constraint violations
        # Order matters: delete children before parent
        
        # 1. Delete evaluation criteria (depends on rounds and job)
        await db.execute(delete(EvaluationCriteria).where(EvaluationCriteria.job_id == job_uuid))
        
        # 2. Delete interview rounds
        await db.execute(delete(RoundList).where(RoundList.job_id == job_uuid))
        
        # 3. Delete job skills
        await db.execute(delete(JobSkills).where(JobSkills.job_id == job_uuid))
        
        # 4. Delete job descriptions
        await db.execute(delete(JobDescription).where(JobDescription.job_id == job_uuid))
        
        # 5. Delete job locations
        await db.execute(delete(JobLocations).where(JobLocations.job_id == job_uuid))
        
        # 6. Finally, delete the job itself
        result = await db.execute(delete(JobDetails).where(JobDetails.id == job_uuid))
        rows_affected = result.rowcount
        
        if rows_affected == 0:
            logger.warning(f"[JobRepo] hard_delete_job_by_id: No job found with id={job_id}")
            await db.commit()
            return False
        
        await db.commit()
        logger.info(f"[JobRepo] hard_delete_job_by_id: Successfully deleted job_id={job_id} and all related records")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"[JobRepo] hard_delete_job_by_id failed: {e}")
        raise


async def hard_delete_jobs_batch(db: AsyncSession, job_ids: List[str]) -> int:
    """
    Permanently delete multiple job posts and all related records from the database.
    This is a HARD DELETE - the data cannot be recovered.
    Returns the number of jobs successfully deleted.
    """
    uuids = []
    for jid in job_ids:
        try:
            uuids.append(uuid.UUID(jid))
        except Exception:
            logger.warning(f"[JobRepo] hard_delete_jobs_batch: Invalid UUID format for {jid}")
            continue
    
    if not uuids:
        logger.warning(f"[JobRepo] hard_delete_jobs_batch: No valid UUIDs provided")
        return 0

    try:
        # Order matters: delete children before parent
        # Complete dependency chain:
        # shortlist → curation → (profiles, job_details)
        # interview_rounds → (profiles, round_list) → job_details
        
        # 1. Delete shortlist first (child of curation, profiles, job_details)
        await db.execute(delete(Shortlist).where(Shortlist.job_id.in_(uuids)))
        
        # 2. Delete curation (child of profiles and job_details, parent of shortlist)
        await db.execute(delete(Curation).where(Curation.job_id.in_(uuids)))
        
        # 3. Delete interview_rounds (child of both profiles and round_list)
        await db.execute(delete(InterviewRounds).where(InterviewRounds.job_id.in_(uuids)))
        
        # 4. Delete profiles (child of job_details, parent of interview_rounds/curation)
        await db.execute(delete(Profile).where(Profile.job_id.in_(uuids)))
        
        # 5. Delete evaluation criteria (child of round_list and job)
        await db.execute(delete(EvaluationCriteria).where(EvaluationCriteria.job_id.in_(uuids)))
        
        # 6. Delete round_list (child of job_details, parent of interview_rounds)
        await db.execute(delete(RoundList).where(RoundList.job_id.in_(uuids)))
        
        # 7. Delete job skills
        await db.execute(delete(JobSkills).where(JobSkills.job_id.in_(uuids)))
        
        # 8. Delete job descriptions
        await db.execute(delete(JobDescription).where(JobDescription.job_id.in_(uuids)))
        
        # 9. Delete job locations
        await db.execute(delete(JobLocations).where(JobLocations.job_id.in_(uuids)))
        
        # 10. Finally, delete the jobs themselves
        result = await db.execute(delete(JobDetails).where(JobDetails.id.in_(uuids)))
        rows_affected = result.rowcount
        
        await db.commit()
        logger.info(f"[JobRepo] hard_delete_jobs_batch: Successfully deleted {rows_affected} job(s) and all related records")
        return rows_affected
        
    except Exception as e:
        await db.rollback()
        logger.error(f"[JobRepo] hard_delete_jobs_batch failed: {e}")
        raise

