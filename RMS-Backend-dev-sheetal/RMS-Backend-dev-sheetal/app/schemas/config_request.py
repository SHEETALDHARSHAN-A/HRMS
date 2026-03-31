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
    codingEnabled: bool = Field(default=False, description="Enable coding challenge for this round")
    codingQuestionMode: str = Field(default="ai", description="Question source mode: 'ai' or 'provided'")
    codingDifficulty: str = Field(default="medium", description="Coding difficulty: easy/medium/hard")
    codingQuestionCount: int = Field(default=1, ge=1, le=20, description="Number of coding questions to generate")
    codingQuestionType: Optional[str] = Field(default=None, description="Coding question type (e.g., dsa/sql/debugging)")
    codingCategories: List[str] = Field(default_factory=list, description="Coding question categories/topics")
    codingCustomQuestions: List[str] = Field(default_factory=list, description="Custom coding prompts to prioritize")
    codingLanguages: List[str] = Field(default_factory=lambda: ["python"], description="Allowed submission languages")
    providedCodingQuestion: Optional[str] = Field(None, description="Admin-provided coding question text")
    codingTestCaseMode: str = Field(default="ai", description="Coding test-case source mode: 'ai' or 'provided'")
    codingTestCases: List[Dict[str, Any]] = Field(default_factory=list, description="Configured coding test cases")
    codingStarterCode: Dict[str, str] = Field(default_factory=dict, description="Optional starter code by language")
    mcqEnabled: bool = Field(default=False, description="Enable MCQ challenge for this round")
    mcqQuestionMode: str = Field(default="ai", description="MCQ source mode: 'ai' or 'provided'")
    mcqDifficulty: str = Field(default="medium", description="MCQ difficulty: easy/medium/hard")
    mcqQuestionCount: int = Field(default=5, ge=1, le=100, description="Number of MCQ/apti questions")
    mcqQuestionType: Optional[str] = Field(default=None, description="MCQ/apti question type")
    mcqCategories: List[str] = Field(default_factory=list, description="MCQ/apti categories/topics")
    mcqCustomQuestions: List[Any] = Field(default_factory=list, description="Optional custom MCQ/apti questions (dicts or prompt strings)")
    aptiQuestionCount: Optional[int] = Field(default=None, ge=1, le=100, description="Alias for MCQ question count")
    aptiQuestionType: Optional[str] = Field(default=None, description="Alias for MCQ/apti question type")
    aptiCategories: List[str] = Field(default_factory=list, description="Alias for MCQ/apti categories")
    aptiCustomQuestions: List[Any] = Field(default_factory=list, description="Alias for MCQ/apti custom questions")
    mcqQuestions: List[Dict[str, Any]] = Field(default_factory=list, description="MCQ question bank with options")
    mcqPassingScore: int = Field(default=60, ge=0, le=100, description="Passing score percentage for MCQ challenge")

    class Config:
        from_attributes = True # Allow easy conversion from ORM objects

class AgentConfigUpdateRequest(BaseModel):
    """
    The main request body sent from the frontend, containing all
    round configurations for a job.
    """
    agentRounds: List[AgentRoundConfigUpdate] = Field(..., description="List of all round configurations for the job")