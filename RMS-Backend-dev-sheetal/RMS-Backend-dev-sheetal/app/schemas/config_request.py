# app/schemas/config_request.py

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uuid

# --- PREVIEW SCHEMAS ---
class EmailTemplatePreviewRequest(BaseModel):
    template_subject: str = Field(..., description="The template string for the email subject (e.g., '{{JOB_TITLE}} Interview')")
    template_body: str = Field(..., description="The HTML template string for the email body.")
    sample_context: Dict[str, str | Any] = Field(
        ..., 
        description="Dictionary containing key-value pairs of sample data for placeholders."
    )

class EmailTemplatePreviewResponse(BaseModel):
    rendered_subject: str = Field(..., description="The subject after placeholder substitution.")
    rendered_html_body: str = Field(..., description="The HTML body after placeholder substitution.")

# --- UPDATE/SAVE SCHEMA ---
class EmailTemplateUpdateRequest(BaseModel):
    template_key: str = Field(..., description="Unique key identifying the template type (e.g., 'interview_invite')")
    subject_template: str = Field(..., description="The new custom subject template.")
    body_template_html: str = Field(..., description="The new custom body HTML template.")


# Assuming this is in app/schemas/config_request.py

class EmailTemplateResponse(BaseModel):
    # What the client loads into editable fields (RAW)
    template_key: str 
    subject_template: str
    body_template_html: str

# --- AGENT CONFIG SCHEMAS ---

class AgentRoundConfigUpdate(BaseModel):
    """
    Payload for a single round's configuration.
    Matches the frontend's AgentRoundConfig interface.
    'id' is the AgentRoundConfig.id, 'roundListId' is the RoundList.id
    """
    id: Optional[str] = Field(None, description="Existing config ID (if any, e.g., 'new_...' or a real UUID)")
    jobId: str = Field(..., description="Job ID this config belongs to")
    
    # This is the ID from the 'round_list' table, which defines the round
    roundListId: str = Field(..., description="The ID of the job round this config applies to")
    
    roundName: str = Field(..., description="Name of the round")
    roundFocus: str = Field(..., description="The main prompt/objective for the agent")
    persona: str = Field(default='alex', description="Agent persona (e.g., 'alex')")
    keySkills: List[str] = Field(default_factory=list)
    customQuestions: List[str] = Field(default_factory=list)
    forbiddenTopics: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True # Allow easy conversion from ORM objects

class AgentConfigUpdateRequest(BaseModel):
    """
    The main request body sent from the frontend, containing all
    round configurations for a job.
    """
    agentRounds: List[AgentRoundConfigUpdate] = Field(..., description="List of all round configurations for the job")