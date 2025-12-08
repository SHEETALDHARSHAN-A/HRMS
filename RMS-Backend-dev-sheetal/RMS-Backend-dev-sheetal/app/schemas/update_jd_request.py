# app/schemas/update_jd_request.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from typing import Any
from pydantic import model_validator

# ---- SKILL SCHEMA ----
class SkillSchema(BaseModel):
    skill: str = Field(..., description="Skill name, e.g., Python, React, ML.")
    weightage: int = Field(..., ge=1, le=10, description="Importance weight (1-10).")


# ---- DESCRIPTION SECTION SCHEMA ----
class DescriptionSection(BaseModel):
    title: str = Field(..., description="Section title, e.g., 'Context', 'Roles and Responsibilities'.")
    content: str = Field(..., description="Detailed content for the section.")


class InterviewRoundSchema(BaseModel):
    level_name: str = Field(..., description="Round name, e.g., 'Initial Screening', 'Technical', 'HR'.")
    description: Optional[str] = Field(None, description="Description or focus of this round.")
    round_order: int = Field(..., ge=1, description="Order of the round in the interview process.")

    shortlisting_threshold: int = Field(..., ge=0, le=100, description="Shortlisting threshold (0-100).")
    rejected_threshold: int = Field(..., ge=0, le=100, description="Rejecting threshold (0-100).") 

   
# ---- MAIN REQUEST SCHEMA ----
class UpdateJdRequest(BaseModel):
    job_id: Optional[str] = Field(None, description="UUID of the job post (required for updates).")
    job_title: str
    job_description: Optional[str] # Keep this, your frontend is sending it
    description_sections: Optional[List[DescriptionSection]]

    minimum_experience: int = Field(0, ge=0)
    maximum_experience: int = Field(0, ge=0)
    no_of_openings: int = Field(1, ge=1)
    active_till: datetime

    work_mode: Optional[str] = Field("office", description="'office' | 'remote' | 'hybrid' | 'wfh'")
    job_location: Optional[str]
    job_state : Optional[str]  = Field(None, description="State of the job location.")
    job_country : Optional[str] = Field(None, description="Country of the job location.")

    work_from_home: bool = Field(False)
    skills_required: List[SkillSchema]
    
    # Dynamic Interview Levels
    interview_rounds: Optional[List[InterviewRoundSchema]] = Field(
        None, description="List of interview levels including initial screening."
    )

    role_fit: int = Field(0, ge=0, le=100)
    potential_fit: int = Field(0, ge=0, le=100)
    location_fit: int = Field(0, ge=0, le=100)

    is_active: bool = Field(True)

    # Per-round agent configuration (optional): accepts either camelCase or snake_case keys
    agent_configs: Optional[List[dict]] = Field(
        None,
        description="Optional per-round agent configurations. If provided, these will be persisted as AgentRoundConfig entries."
    )

    # --- START OF FIX: Add these missing fields ---
    career_activation_mode: Optional[str] = Field("manual", description="Activation mode: manual, days, shortlist")
    career_activation_days: Optional[int] = Field(30, description="Days to auto-disable job")
    career_shortlist_threshold: Optional[int] = Field(0, description="Shortlist count to auto-disable job")
    # Salary fields (accept both canonical and legacy keys)
    minimum_salary: Optional[int] = Field(None, description="Minimum annual salary in smallest currency unit (e.g., cents or rupee)")
    maximum_salary: Optional[int] = Field(None, description="Maximum annual salary in smallest currency unit")
    # Legacy/alternate keys that some frontends may send
    min_salary: Optional[int] = Field(None, alias="min_salary")
    max_salary: Optional[int] = Field(None, alias="max_salary")
    # --- END OF FIX ---

    @field_validator("maximum_experience")
    def validate_experience(cls, v, info):
        min_exp = info.data.get("minimum_experience", 0)
        if v < min_exp:
            raise ValueError("Maximum experience must be greater than or equal to minimum experience")
        return v

    @model_validator(mode='before')
    def coerce_salary_keys(cls, values: dict) -> dict:
        """Allow payloads that include `min_salary`/`max_salary` to populate
        `minimum_salary`/`maximum_salary`. This runs before validation.
        """
        if not isinstance(values, dict):
            return values
        if 'min_salary' in values and 'minimum_salary' not in values:
            values['minimum_salary'] = values.get('min_salary')
        if 'max_salary' in values and 'maximum_salary' not in values:
            values['maximum_salary'] = values.get('max_salary')
        return values