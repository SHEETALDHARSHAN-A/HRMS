# src/service/curate_profiles.py

import re
import uuid
import json
import redis.asyncio as redis

from uuid import UUID
from agents import Agent, Runner
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.prompts.curation_prompt import RESUME_CURATION_PROMPT
from src.db.repository.curation_repository import CurationRepository

# Fallback channel constant for robustness
DEFAULT_STATUS_CHANNEL = "ATS_JOB_STATUS" 


# ======================================================================
# SCORING LOGIC
# ======================================================================

class ScoringLogic:
    """
    Handles weighted evaluation logic for LLM curation.
    """
    
    def _get_score_from_llm_block(self, block: Dict[str, Any], key: str) -> int:
        """
        Safely retrieves the integer score (0-100) from an LLM output block.
        """
        val = block.get(key)
        
        if isinstance(val, dict):
            try:
                return int(val.get("score", 0))
            except (TypeError, ValueError):
                return 0
        
        try:
            return int(val) if val is not None else 0
        except (TypeError, ValueError):
            return 0
    
    async def process(
        self,
        llm_output: Dict[str, Any],
        job_details: Dict[str, Any],
        existing_scores: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process LLM output and compute final weighted scores.
        """
        # Check existing scores early to prevent re-processing
        profile_id_str = llm_output.get("profile_id") or llm_output.get("profileId")
        if existing_scores and str(existing_scores.get("profile_id")) == str(profile_id_str):
            print(f"[INFO] Using existing scores for profile {profile_id_str}")
            return existing_scores
            
        name = llm_output.get("name", "Unknown")
        email = llm_output.get("email", "")
        location_from_llm = llm_output.get("location", "")

        # ========================================
        # 1. SKILLS EVALUATION
        # ========================================
        llm_skills = llm_output.get("skills_score") or llm_output.get("skills_evaluation", {}) or {}
        
        job_skills_list: List[Dict] = job_details.get("skills_required", []) or []
        min_exp = float(job_details.get("minimum_experience") or 0)
        max_exp = job_details.get("maximum_experience")
        if max_exp is not None:
            max_exp = float(max_exp)
        
        work_from_home = bool(
            job_details.get("work_from_home") or
            (str(job_details.get("work_mode") or "").lower() in ("remote", "hybrid", "wfh"))
        )

        total_skill_weight = sum([s.get("weightage", 0) for s in job_skills_list]) or 0
        skill_score_explanation: Dict[str, Dict[str, Any]] = {}
        weighted_skill_sum = 0.0

        for job_skill in job_skills_list:
            skill_name = job_skill.get("name")
            weightage = job_skill.get("weightage", 0) or 0
            raw_entry = llm_skills.get(skill_name)

            # Parse skill score from LLM output
            if isinstance(raw_entry, dict):
                score_100 = int(raw_entry.get("score", 0))
                explanation = raw_entry.get("explanation", "").strip() or "No evidence found."
                evidence = raw_entry.get("evidence", "").strip() or "No evidence."
            else:
                score_100 = 0
                explanation = "No evidence found."
                evidence = "No evidence."

            score_100 = max(0, min(100, score_100))
            skill_score_explanation[skill_name] = {
                "score_100": score_100,
                "explanation": explanation,
                "evidence": evidence
            }

            if total_skill_weight > 0:
                weighted_skill_sum += (score_100 * weightage)

        # Compute overall skill score
        if total_skill_weight > 0:
            overall_skill_score = int(round(weighted_skill_sum / total_skill_weight))
        else:
            if llm_skills:
                scores = [
                    int(v.get("score", 0)) if isinstance(v, dict) else 0
                    for v in llm_skills.values()
                ]
                overall_skill_score = int(round(sum(scores) / len(scores))) if scores else 0
            else:
                overall_skill_score = 0

        # ========================================
        # 2. OVERALL MATCH SCORES
        # ========================================
        if "overall_match" in llm_output:
            # Old nested format
            llm_overall = llm_output.get("overall_match", {}) or {}
            role_fit_score = self._get_score_from_llm_block(llm_overall, "Role Fit")
            potential_score = self._get_score_from_llm_block(llm_overall, "Potential")
            location_score = self._get_score_from_llm_block(llm_overall, "Location")
        else:
            # New flat format
            role_fit_score = int(llm_output.get("overall_role_fit", 0))
            potential_score = int(llm_output.get("overall_potential", 0))
            location_score = int(llm_output.get("location_score", 0))

        # Override location score for remote jobs
        if work_from_home:
            location_score = 100

        # ========================================
        # 3. EXPERIENCE ADJUSTMENTS
        # ========================================
        candidate_years = float(llm_output.get("total_years_of_experience", 0) or 0)
        
        # Penalty for insufficient experience
        if min_exp > 0 and candidate_years < min_exp:
            years_missing = max(0.0, min_exp - candidate_years)
            penalty = min(30, int(round(years_missing * 5)))
            role_fit_score = max(0, role_fit_score - penalty)
            potential_score = max(0, potential_score - int(penalty / 2))

        # Penalty for overqualification
        if max_exp is not None and candidate_years > max_exp:
            years_over = max(0.0, candidate_years - max_exp)
            over_penalty = min(10, int(round(years_over)))
            role_fit_score = max(0, role_fit_score - over_penalty)

        # ========================================
        # 4. WEIGHTED FINAL SCORE CALCULATION
        # ========================================
        # Retrieve weights with fallback defaults
        role_w = float(job_details.get("role_fit_weight", 0) or 0)
        potential_w = float(job_details.get("potential_fit_weight", 0) or 0)
        location_w = float(job_details.get("location_fit_weight", 0) or 0)
        
        # Apply default weights if all are zero
        if role_w == 0 and potential_w == 0 and location_w == 0:
            print("[WARN] [SCORING] All weights are 0. Using default weights: 40/30/30")
            role_w, potential_w, location_w = 40.0, 30.0, 30.0
        
        sum_three = role_w + potential_w + location_w

        # Calculate skill weight
        if sum_three >= 100:
            skill_w = 0.0
            total_weight = sum_three
        else:
            skill_w = 100.0 - sum_three
            total_weight = 100.0
            
        # Final fallback - should never reach here
        if total_weight == 0:
            print("[ERROR] [SCORING] Total weight is still 0 after fallbacks. Using equal weights.")
            role_w = potential_w = location_w = skill_w = 25.0
            total_weight = 100.0

        # Compute weighted overall score
        overall_score = int(round(
            (role_fit_score * (role_w / total_weight)) +
            (potential_score * (potential_w / total_weight)) +
            (location_score * (location_w / total_weight)) +
            (overall_skill_score * (skill_w / total_weight))
        ))

        print(
            f"[INFO] [SCORING] Final Score: {overall_score} "
            f"(Role: {role_fit_score}*{role_w/total_weight:.2f} + "
            f"Potential: {potential_score}*{potential_w/total_weight:.2f} + "
            f"Location: {location_score}*{location_w/total_weight:.2f} + "
            f"Skills: {overall_skill_score}*{skill_w/total_weight:.2f})"
        )

        # ========================================
        # 5. CATEGORIZATION
        # ========================================
        shortlisting_threshold = int(job_details.get("shortlisting_criteria", 70))
        rejecting_threshold = int(job_details.get("rejecting_criteria", 40))

        if overall_score >= shortlisting_threshold:
            curated_result = "shortlisted"
        elif overall_score <= rejecting_threshold:
            curated_result = "rejected"
        else:
            curated_result = "under_review"

        # ========================================
        # 6. BUILD FINAL SKILLS SCORE LIST
        # ========================================
        final_skills_score_list = [
            {
                "skill": skill_name,
                "job_skill_id": job_skill.get("skill_id"),
                "weightage": job_skill.get("weightage", 0),
                "score_100": entry["score_100"],
                "explanation": entry["explanation"],
                "evidence": entry["evidence"]
            }
            for skill_name, entry in skill_score_explanation.items()
            for job_skill in job_skills_list if job_skill.get("name") == skill_name
        ]

        # ========================================
        # 7. RETURN FINAL RESULT
        # ========================================
        return {
            "profile_id": UUID(str(profile_id_str)) if profile_id_str else uuid.uuid4(),
            "name": name,
            "email": email,
            "location": location_from_llm,
            "years_of_experience": candidate_years,
            "skill_match_score": overall_skill_score,
            "potential_score": potential_score,
            "location_fit_score": location_score,
            "role_fit_score": role_fit_score,
            "overall_score": overall_score,
            "curated_results": curated_result,
            "match_summary": llm_output.get("match_summary", ""),
            "score_breakdown": {
                "weights_applied": {
                    "role": role_w,
                    "potential": potential_w,
                    "location": location_w,
                    "skills": skill_w
                },
                "skill_score_explanation": skill_score_explanation
            },
            "skills_score": final_skills_score_list
        }


# ======================================================================
# CURATION PIPELINE
# ======================================================================

class CurateProfiles:
    """Pipeline for LLM-based resume curation, scoring, and DB storage."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the curation service.
        """
        self.db_session = db_session
        self.curation_repo = CurationRepository(db_session)
        self.scorer = ScoringLogic()
        # Set status channel, defaulting if not provided
        self.status_channel = DEFAULT_STATUS_CHANNEL 
        
        print("[INFO] CurateProfiles service initialized")

    async def publish_progress(
        self,
        redis_client: redis.Redis,
        task_id: str,
        job_id: str,
        message: str,
        stage: str,
        progress: int,
        file_name: str = "",
        profile_id: str = ""
    ):
        """
        Publish progress updates to Redis channel and stream.
        """
        payload = {
            "task_id": task_id,
            "job_id": job_id,
            "file_name": file_name,
            "profile_id": profile_id,
            "stage": stage,
            "processing_percentage": int(round(progress)),
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            # Publish to channel
            await redis_client.publish(self.status_channel, json.dumps(payload))
            
            # Add to stream for persistence
            await redis_client.xadd(
                f"{self.status_channel}:stream",
                {"payload": json.dumps(payload)}
            )
            
        except Exception as e:
            print(f"[ERROR] [REDIS ERROR] Failed to publish progress: {e}")

    async def process_curation_logic(
        self,
        job_id: str,
        task_id: str,
        profile_ids: Optional[List[str]] = None,
        redis_client: Optional[redis.Redis] = None,
        status_channel: Optional[str] = None,
    ) -> Dict:
        """
        Main curation pipeline entrypoint.
        """
        # Set status channel override
        if status_channel:
            self.status_channel = status_channel

        try:
            job_uuid = UUID(job_id)
            
            # Ensure fresh transaction view
            await self.db_session.rollback() 
            
            # ========================================
            # 1. FETCH JOB CONFIGURATION
            # ========================================
            print(f"[INFO] Fetching job configuration for job {job_id}")
            
            job_details_model = await self.curation_repo.fetch_job_configuration(job_uuid)
            if not job_details_model:
                raise ValueError(f"Job not found for job_id: {job_id}")

            # Extract criteria, skills, locations, and build job details dictionaries
            shortlisting_threshold = 70
            rejecting_threshold = 40
            job_skills_list = []
            job_locations = []
            
            # Extract criteria from RoundList
            for r in getattr(job_details_model, "rounds", []) or []:
                if getattr(r, "round_order", 0) == 1:
                    for ec in getattr(r, "evaluation_criteria", []) or []:
                        shortlisting_threshold = getattr(ec, "shortlisting_criteria", shortlisting_threshold)
                        rejecting_threshold = getattr(ec, "rejecting_criteria", rejecting_threshold)
                        break
                    break

            # Extract job skills
            for js in getattr(job_details_model, "job_skills", []) or []:
                skill_name = getattr(js.skill, "skill_name", None) or getattr(js.skill, "skill", None)
                if skill_name:
                    job_skills_list.append({"name": skill_name, "weightage": getattr(js, "weightage", 0), "skill_id": getattr(js, "skill_id", None)})

            # Extract job locations
            for loc_detail in getattr(job_details_model, "location_details", []) or []:
                job_locations.append({"city": loc_detail.get("location_name", ""), "state": loc_detail.get("state", ""), "country": loc_detail.get("country", "")})

            # Build job details for LLM prompt
            job_details_for_prompt = {
                "job_title": getattr(job_details_model, "job_title", ""),
                "job_description": getattr(job_details_model, "full_description_text", ""), 
                "skills_required": [s["name"] for s in job_skills_list],
                "minimum_experience": getattr(job_details_model, "minimum_experience", 0),
                "maximum_experience": getattr(job_details_model, "maximum_experience", None),
                "work_mode": getattr(job_details_model, "work_mode", None),
                "job_location": job_locations
            }

            # Build job details for scoring
            job_details_for_scoring = {
                "job_id": job_uuid,
                "job_location": job_locations,
                "role_fit_weight": getattr(job_details_model, "role_fit", 0) or 0,
                "potential_fit_weight": getattr(job_details_model, "potential_fit", 0) or 0,
                "location_fit_weight": getattr(job_details_model, "location_fit", 0) or 0,
                "shortlisting_criteria": int(shortlisting_threshold),
                "rejecting_criteria": int(rejecting_threshold),
                "work_from_home": getattr(job_details_model, "work_from_home", False) or (str(getattr(job_details_model, "work_mode", "")).lower() in ("remote", "hybrid", "wfh")),
                "work_mode": getattr(job_details_model, "work_mode", None),
                "minimum_experience": getattr(job_details_model, "minimum_experience", 0),
                "maximum_experience": getattr(job_details_model, "maximum_experience", None),
                "skills_required": job_skills_list
            }

            # ========================================
            # 2. FETCH PROFILES TO CURATE
            # ========================================
            profiles_to_fetch = profile_ids if profile_ids and len(profile_ids) > 0 else None
            profiles = await self.curation_repo.fetch_profiles(job_uuid, profile_ids=profiles_to_fetch)
            
            # SAFETY CHECK: Filter out any profiles with invalid extracted_content
            valid_profiles = []
            for profile in profiles:
                extracted_content = getattr(profile, "extracted_content", {}) or {}
                if isinstance(extracted_content, str):
                    try:
                        extracted_content = json.loads(extracted_content)
                    except Exception:
                        extracted_content = {}
                
                # Skip profiles that were marked as invalid (is_valid_resume = False)
                if extracted_content.get("is_valid_resume") is False:
                    print(f"[WARN] Skipping invalid profile {getattr(profile, 'id', 'unknown')} "
                          f"(detected as {extracted_content.get('detected_type', 'non-resume')})")
                    continue
                
                valid_profiles.append(profile)
            
            profiles = valid_profiles
            
            if not profiles:
                await self.publish_progress(redis_client, task_id, job_id, "No valid resumes found for curation.", "completed", 100)
                return {"success": True, "message": "No valid resumes found for curation."}

            total_files = len(profiles)
            final_results = []

            print(f"[INFO] Starting curation for {total_files} valid profiles")

            # ========================================
            # 3. PROCESS EACH PROFILE
            # ========================================
            for idx, profile in enumerate(profiles):
                file_name = getattr(profile, "file_name", f"profile_{idx}")
                profile_id = str(getattr(profile, "id", uuid.uuid4()))

                # Extract profile data (Robust step: handling potential string JSON)
                extracted_data = getattr(profile, "extracted_content", {}) or {}
                if isinstance(extracted_data, str):
                    try:
                        extracted_data = json.loads(extracted_data)
                    except Exception:
                        extracted_data = {}

                # Create standardized input data for LLM
                resume_input_data = {
                    "name": getattr(profile, "name", "") or extracted_data.get("name"),
                    "email": getattr(profile, "email", "") or extracted_data.get("email"),
                    "skills": extracted_data.get("skills", []),
                    "experience": extracted_data.get("experience", []),
                    "education": extracted_data.get("education", []),
                    "projects": extracted_data.get("projects", []),
                    "certifications": extracted_data.get("certifications", []),
                    "location": extracted_data.get("location", ""),
                    "summary": extracted_data.get("summary", ""),
                }

                await self.publish_progress(
                    redis_client, task_id, job_id,
                    f"Curation started for {file_name}.",
                    "curation_in_progress", 50 + int((idx / total_files) * 50),
                    file_name, profile_id
                )

                try:
                    # 3a. INVOKE LLM AGENT
                    agent = Agent(name="Resume Curation Agent", instructions=RESUME_CURATION_PROMPT)
                    resume_text_string = json.dumps(resume_input_data, ensure_ascii=False)
                    input_payload = json.dumps({"Resume Text": resume_text_string, "Job Details": job_details_for_prompt})
                    llm_output_run = await Runner.run(agent, [{"role": "user", "content": input_payload}])

                    # 3b. PARSE LLM OUTPUT (Robust step)
                    json_match = re.search(r'```(?:jsonc?|)\n(.*)```', llm_output_run.final_output, re.DOTALL)
                    json_string = json_match.group(1).strip() if json_match else llm_output_run.final_output.strip()
                    raw_llm_json = json.loads(json_string)
                    
                    raw_llm_json["profile_id"] = profile_id

                    # 3c. COMPUTE SCORES
                    curated_result = await self.scorer.process(raw_llm_json, job_details_for_scoring)

                    # 3d. MAP TO DATABASE SCHEMA
                    mapped = {
                        "job_id": job_uuid,
                        "profile_id": UUID(profile_id),
                        "potential_score": int(curated_result["potential_score"]),
                        "location_score": int(curated_result["location_fit_score"]),
                        "role_fit_score": int(curated_result["role_fit_score"]),
                        "skill_score": int(curated_result["skill_match_score"]),
                        "skill_score_explanation": curated_result["score_breakdown"]["skill_score_explanation"],
                        "overall_score": int(curated_result["overall_score"]),
                        "result": curated_result["curated_results"],
                        "explanation": curated_result.get("match_summary", "")
                    }

                    final_results.append(mapped)

                    await self.publish_progress(
                        redis_client, task_id, job_id,
                        f"[RESULT] {file_name} -> {mapped['result']} ({mapped['overall_score']}/100)",
                        "curation_complete", 50 + int(((idx + 1) / total_files) * 50),
                        file_name, profile_id
                    )

                    print(f"[INFO] [CURATION] Profile {profile_id} -> {mapped['result']} ({mapped['overall_score']}/100)")

                except Exception as e:
                    # Edge Case: LLM failure or score computation failure
                    print(f"[ERROR] [CURATION ERROR] Failed for {file_name}: {type(e).__name__} - {str(e)}")
                    
                    await self.publish_progress(
                        redis_client, task_id, job_id,
                        f"Curation failed for {file_name}: {type(e).__name__}",
                        "failed_curation", 50 + int(((idx + 1) / total_files) * 50),
                        file_name, profile_id
                    )
                    continue

            # ========================================
            # 4. SAVE RESULTS TO DATABASE
            # ========================================
            if final_results:
                print(f"[INFO] Saving {len(final_results)} curation results to database")
                await self.curation_repo.save_curation_results(final_results)

            # CRITICAL FIX: Check if all profiles were successfully curated
            success_count = len(final_results)
            if success_count < total_files:
                error_message = f"Curation failed for {total_files - success_count} profile(s) due to external errors (e.g., API quota)."
                print(f"[ERROR] {error_message}")
                
                # Do not commit final status update on failure, allow retry.
                return {
                    "success": False,
                    "message": error_message,
                }
            
            await self.publish_progress(redis_client, task_id, job_id, "Curation completed successfully.", "completed", 100)
            
            print(f"[INFO] Curation complete for job {job_id}: {success_count} profiles processed")
            
            return {
                "success": True, 
                "message": f"Curation complete for {success_count} profiles."
            }


        except RuntimeError as e:
            # Database Transaction Failure (Edge Case)
            print(f"[ERROR] [DATABASE ERROR] {str(e)}")
            await self.publish_progress(redis_client, task_id, job_id, f"Database Error: {str(e)}", "failed", 100)
            raise HTTPException(status_code=500, detail=f"Database transaction failed: {str(e)}") from e
        
        except Exception as e:
            # Catch-all Service Failure (Edge Case)
            print(f"[ERROR] [CURATION SERVICE ERROR] {type(e).__name__} - {str(e)}")
            
            await self.publish_progress(redis_client, task_id, job_id, f"Service Error: {str(e)}", "failed", 100)
            raise HTTPException(status_code=500, detail=f"Curation service failed: {str(e)}") from e
