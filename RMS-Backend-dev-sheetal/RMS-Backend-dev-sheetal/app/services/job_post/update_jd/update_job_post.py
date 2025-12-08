# app/services/job_post/update_jd/update_job_post.py

import uuid

from datetime import datetime, timezone
from fastapi import HTTPException, status
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.update_jd_request import UpdateJdRequest
from app.db.repository.job_post_repository import (
    update_or_create_job_details,
    get_job_details_by_id,
)
from app.services.job_post.job_post_serializer import serialize_job_details


class UpdateJobPost:
    """
    Service for updating or creating (UPSERT) job posts.
    Handles validations, ID generation, and repository calls.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_job_post(
        self,
        job_details: UpdateJdRequest,
        job_id: Optional[str] = None,
        creator_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates an existing job post if job_id is provided,
        otherwise creates a new post by generating a UUID.
        
        Args:
            job_details: The job post data from the request
            job_id: Optional UUID of existing job to update
            creator_id: Optional UUID of the user creating/updating the job
        """
        try:
            # -------------------- 1. Validation --------------------
            # Validate minimum/maximum experience early to avoid running
            # other logic (and to allow tests that pass simple objects)
            min_exp = getattr(job_details, "minimum_experience", None)
            max_exp = getattr(job_details, "maximum_experience", None)
            if min_exp is not None and max_exp is not None and min_exp > max_exp:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Minimum experience cannot be greater than maximum experience."
                )

            # -------------------- 2. Job ID Handling --------------------
            if job_id:
                processed_job_id = job_id
                action = "UPDATE"
            else:
                processed_job_id = str(uuid.uuid4())
                action = "CREATE"

            print(f"[INFO] Preparing to {action} job post with ID: {processed_job_id}")
            print(f"[DEBUG SERVICE] Job details received:")
            print(f"  - job_title: {getattr(job_details, 'job_title', 'NOT SET')}")
            print(f"  - minimum_experience: {getattr(job_details, 'minimum_experience', 'NOT SET')}")
            print(f"  - maximum_experience: {getattr(job_details, 'maximum_experience', 'NOT SET')}")
            print(f"  - job_location: {getattr(job_details, 'job_location', 'NOT SET')}")

            # -------------------- 3a. Prepare Skills Data --------------------
            skills_data: List[Dict[str, Any]] = [
                {"skill_name": skill.skill, "weightage": skill.weightage}
                for skill in getattr(job_details, "skills_required", []) or []
            ]

            # -------------------- 3b. Prepare Description Sections --------------------
            description_data: List[Dict[str, Any]] = [
                {"type_description": section.title, "context": section.content}
                for section in getattr(job_details, "description_sections", []) or []
            ] if getattr(job_details, "description_sections", None) else None

            # -------------------- 3c. Prepare Interview Rounds (Data Prep) --------------------
            # The schema now enforces thresholds for all rounds.
            rounds_data: List[Dict[str, Any]] = []

            if getattr(job_details, "interview_rounds", None):
                for idx, round_detail in enumerate(job_details.interview_rounds):
                    round_dict = round_detail.model_dump(exclude_unset=True)
                    level_name = round_dict.pop('level_name')
                    
                    round_dict['round_name'] = level_name
                    round_dict['round_description'] = round_dict.pop('description', None)
                    round_dict['round_order'] = round_dict.pop('round_order', idx)

                    evaluation_criteria = {}

                    # --- UPDATED LOGIC: ALL rounds pull thresholds ---
                    # No special casing for index 0. The old fit score logic is completely removed.
                    
                    if "shortlisting_threshold" in round_dict:
                        evaluation_criteria["shortlisting_criteria"] = round_dict.pop("shortlisting_threshold")
                    
                    if "rejecting_threshold" in round_dict:
                        evaluation_criteria["rejecting_criteria"] = round_dict.pop("rejecting_threshold")

                    if evaluation_criteria:
                        round_dict["evaluation_criteria"] = evaluation_criteria

                    rounds_data.append(round_dict)

            if not rounds_data:
                rounds_data = None

            # -------------------- 3e. Prepare Agent Configs --------------------
            # Support incoming `agent_configs` from the request schema (if frontend supplies it)
            agent_configs_data: Optional[List[Dict[str, Any]]] = None

            incoming_agent_configs = getattr(job_details, "agent_configs", None)
            if incoming_agent_configs:
                agent_configs_data = []
                for ac in incoming_agent_configs:
                    # Accept either dicts or pydantic models
                    if isinstance(ac, dict):
                        ac_dict = dict(ac)
                    else:
                        try:
                            ac_dict = ac.model_dump(exclude_unset=True)
                        except Exception:
                            # Fallback: coerce to dict if possible
                            ac_dict = dict(ac)
                    # Only carry forward job-level score metrics into the agent config
                    # when this round represents a screening/initial round. We detect
                    # screening by either an explicit `interview_mode` or by the
                    # round name containing 'screen' or 'initial' (case-insensitive).
                    try:
                        mode = (ac_dict.get('interview_mode') or ac_dict.get('interviewMode') or '').lower()
                        name = (ac_dict.get('roundName') or ac_dict.get('round_name') or '').lower()
                        is_screening = False
                        if mode:
                            is_screening = mode == 'screening' or 'screen' in mode
                        else:
                            is_screening = 'screen' in name or 'initial' in name

                        if is_screening:
                            role_fit_val = getattr(job_details, 'role_fit', None)
                            potential_fit_val = getattr(job_details, 'potential_fit', None)
                            location_fit_val = getattr(job_details, 'location_fit', None)
                            if role_fit_val is not None:
                                ac_dict.setdefault('role_fit', role_fit_val)
                            if potential_fit_val is not None:
                                ac_dict.setdefault('potential_fit', potential_fit_val)
                            if location_fit_val is not None:
                                ac_dict.setdefault('location_fit', location_fit_val)
                    except Exception:
                        pass
                    agent_configs_data.append(ac_dict)

            # -------------------- 3f. Validate Agent Configs (per-round) --------------------
            if agent_configs_data:
                for idx, ac in enumerate(agent_configs_data):
                    mode = (ac.get("interview_mode") or ac.get("interviewMode") or "").lower()

                    if mode == "agent":
                        tmin = ac.get("interview_time_min") or ac.get("interviewTimeMin")
                        tmax = ac.get("interview_time_max") or ac.get("interviewTimeMax")
                        if tmin is None or tmax is None:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Agent interview rounds must include 'interview_time_min' and 'interview_time_max' (round index {idx})."
                            )
                        try:
                            tmin = int(tmin)
                            tmax = int(tmax)
                        except Exception:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Agent interview time bounds must be integers (round index {idx})."
                            )
                        if tmin <= 0 or tmax <= 0 or tmin > tmax:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Invalid interview_time_min/max for agent round (round index {idx})."
                            )

                    if mode in {"offline", "in_person", "inperson", "in-person"}:
                        interviewer = ac.get("interviewer_id") or ac.get("interviewerId")
                        if not interviewer:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"In-person interview rounds must specify an 'interviewer_id' (round index {idx})."
                            )


            # -------------------- 3d. Prepare Job Fields --------------------
            incoming_fields: Dict[str, Any] = job_details.model_dump(
                exclude_unset=True,
                exclude={
                    "skills_required",
                    "description_sections",
                    "interview_rounds",
                    "job_id",
                    "no_of_openings",
                    # REMOVED FIELDS from UpdateJdRequest (that are still on DB model)
                    "role_fit",          
                    "potential_fit",     
                    "location_fit",      
                    # Fields that are NOT columns on JobDetails model:
                    "shortlisting_criteria", 
                    "rejecting_criteria",    
                    "work_from_home",

                    "job_state",    # <--- ADDED TO EXCLUDE
                    "job_country",  

                    "job_location",          
                    "job_description",       
                }
            )

            #
            if 'no_of_openings' in job_details.model_fields_set:
                incoming_fields['no_of_openings'] = job_details.no_of_openings

            # -------------------- 4. Merge Existing Job (for Updates) --------------------
            job_fields: Dict[str, Any] = {}
            existing_job = None

            location_data: List[Dict[str, Any]] = None
            if job_details.job_location:
                location_data = [
                    {
                        "location": job_details.job_location,
                        "state": job_details.job_state,    # <--- NEW DATA MAPPED
                        "country": job_details.job_country,  # <--- NEW DATA MAPPED
                    }
                ]

            if action == "UPDATE":
                try:
                    existing_job = await get_job_details_by_id(self.db, processed_job_id)
                    if existing_job:
                        existing_dict = existing_job.__dict__.copy()
                        # Remove SQLAlchemy internal state and relationship objects
                        existing_dict.pop('_sa_instance_state', None)
                        existing_dict.pop('descriptions', None)
                        existing_dict.pop('locations', None)
                        existing_dict.pop('job_skills', None)
                        existing_dict.pop('rounds', None)
                        existing_dict.pop('creator', None)
                        # Agent configs is a relationship (InstrumentedList) and must not be
                        # passed directly into the SQL UPDATE values mapping.
                        existing_dict.pop('agent_configs', None)
                        # The existing fit-score fields will be preserved as they are not in incoming_fields
                        job_fields = {**existing_dict, **incoming_fields}
                    else:
                        job_fields = {**incoming_fields}
                except Exception as e:
                    print(f"[WARN] Failed to merge existing job data: {e}")
                    job_fields = {**incoming_fields}
            else:
                job_fields = {**incoming_fields}

            # -------------------- 5. Handle Dates and Creator ID --------------------
            if action == "CREATE":
                job_fields["posted_date"] = datetime.now(timezone.utc)
                if "user_id" not in job_fields:
                    if creator_id:
                        job_fields["user_id"] = creator_id
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Missing authenticated user for job creation."
                        )
                try:
                    updated_job = await update_or_create_job_details(
                        db=self.db,
                        job_id=processed_job_id,
                        job_data=job_fields,
                        skills_data=skills_data,
                        description_data=description_data,
                        location_data=location_data,
                        rounds_data=rounds_data,
                        agent_configs_data=agent_configs_data,
                    )
                except ValueError as ve:
                    # Treat ValueError from repository as a client error
                    return {
                        "success": False,
                        "job_details": None,
                        "message": str(ve),
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }
            elif action == "UPDATE":
                # For updates, ensure we don't lose the user_id
                if "user_id" not in job_fields and existing_job:
                    # Preserve original creator
                    job_fields["user_id"] = existing_job.user_id
                elif creator_id and "user_id" not in job_fields:
                    # If no existing job found but we have creator_id, use it
                    job_fields["user_id"] = creator_id

            # No job-level interview_type stored; per-round `agent_configs` define modes.
           
            # Debug: Show final job_fields before repository call
            print(f"[DEBUG SERVICE] Final job_fields being sent to repository:")
            for key, value in job_fields.items():
                print(f"  - {key}: {value}")

            # -------------------- 6. Repository (UPSERT) --------------------
            # For CREATE we already invoked the repository above; only call
            # the repo here for UPDATE flows (or if the CREATE branch didn't
            # produce an updated_job for some reason).
            if action != "CREATE":
                updated_job = await update_or_create_job_details(
                    db=self.db,
                    job_id=processed_job_id,
                    job_data=job_fields,
                    skills_data=skills_data,
                    description_data=description_data,
                    location_data=location_data,
                    rounds_data=rounds_data,
                    agent_configs_data=agent_configs_data,
                )

            if updated_job is None:
                return {
                    "success": False,
                    "job_details": None,
                    "message": f"Failed to {action.lower()} job post.",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                }

            # -------------------- 7. Prepare Response --------------------
            job_payload = serialize_job_details(updated_job)
            job_payload["job_id"] = job_payload.get("job_id") or processed_job_id
            job_payload.pop("user_id", None)

            print(f"[DEBUG SERVICE] Serialized job data for response:")
            print(f"  - job_title: {job_payload.get('job_title', 'NOT SET')}")
            print(f"  - minimum_experience: {job_payload.get('minimum_experience', 'NOT SET')}")
            print(f"  - maximum_experience: {job_payload.get('maximum_experience', 'NOT SET')}")
            print(f"  - job_location: {job_payload.get('job_location', 'NOT SET')}")
            print(f"  - is_active: {job_payload.get('is_active', 'NOT SET')}")

            print(f"[INFO] Job post {action} successful: {processed_job_id}")

            return {
                "success": True,
                "job_details": job_payload,
                "message": f"Job post {action.lower()}d successfully."
            }

        except HTTPException as he:
            return {
                "success": False,
                "job_details": None,
                "message": he.detail,
                "status_code": he.status_code,
            }

        except Exception as e:
            print(f"[CRIT] Unexpected error during job {action}: {e}")
            return {
                "success": False,
                "job_details": None,
                "message": "Unexpected error occurred while updating/creating job.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    async def toggle_status(self, job_id: str, is_active: bool) -> Dict[str, Any]:
        """
        Toggle the 'is_active' flag for a job post and return a StandardResponse-like dict.
        """
        try:
            # Import here to avoid circular imports at module level
            from app.db.repository.job_post_repository import set_job_active_status

            print(f"[SERVICE] toggle_status called for job_id={job_id} is_active={is_active}")

            updated = await set_job_active_status(self.db, job_id=job_id, is_active=is_active)
            if not updated:
                print(f"[SERVICE] toggle_status: no job found for id={job_id}")
                return {
                    "success": False,
                    "job_details": None,
                    "message": "Invalid job id or job not found",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }

            payload = serialize_job_details(updated)
            # Ensure the payload reflects the requested status (defensive)
            payload["is_active"] = bool(is_active)
            payload.pop("user_id", None)

            print(f"[SERVICE] toggle_status succeeded for job_id={job_id} new_is_active={payload.get('is_active')}")

            return {
                "success": True,
                "data": {"job_details": payload},
                "message": f"Job post {job_id} status toggled to {is_active}.",
                "status_code": status.HTTP_200_OK,
            }
        except Exception as e:
            print(f"[CRIT] toggle_status failed: {e}")
            return {
                "success": False,
                "job_details": None,
                "message": "Failed to toggle job status.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    async def delete_job_post(self, job_id: str) -> Dict[str, Any]:
        """
        Permanently delete a job post and all related records from the database.
        This is a HARD DELETE - the data cannot be recovered.
        """
        try:
            from app.db.repository.job_post_repository import hard_delete_job_by_id

            print(f"[SERVICE] delete_job_post called for job_id={job_id}")

            ok = await hard_delete_job_by_id(self.db, job_id)
            if not ok:
                print(f"[SERVICE] delete_job_post: no job found for id={job_id}")
                return {
                    "success": False,
                    "message": "Invalid job id or job not found",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }

            print(f"[SERVICE] delete_job_post: hard-delete succeeded (permanently deleted) for id={job_id}")
            return {
                "success": True,
                "data": {"job_id": job_id, "deleted": True},
                "message": f"Job post {job_id} permanently deleted from database.",
                "status_code": status.HTTP_200_OK,
            }
        except Exception as e:
            print(f"[CRIT] delete_job_post failed: {e}")
            return {
                "success": False,
                "message": "Failed to delete job post.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    # Backwards-compatible alias used by some tests and older callers
    async def update_job_post_service(self, job_details: UpdateJdRequest, caller_id: Optional[str] = None):
        """Compatibility wrapper that delegates to `update_job_post` so tests
        and older code calling `update_job_post_service` continue to work.
        """
        return await self.update_job_post(job_details, None, caller_id)