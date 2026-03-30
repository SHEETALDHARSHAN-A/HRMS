from typing import Any, Dict, Optional
from typing import List

from pydantic import BaseModel, EmailStr, Field


class McqAnswerItem(BaseModel):
    questionId: str = Field(..., min_length=1, max_length=128)
    selectedOptionId: str = Field(..., min_length=1, max_length=128)


class CodingSubmitRequest(BaseModel):
    token: str = Field(..., min_length=6, description="Interview token")
    email: EmailStr
    challengeType: str = Field(default="coding", description="Submission type: coding or mcq")
    language: Optional[str] = Field(default="python", min_length=2, max_length=32)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50000)
    mcqAnswers: List[McqAnswerItem] = Field(default_factory=list)
    question: Optional[Dict[str, Any]] = Field(default=None)
    secureBrowserMeta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional secure-browser metadata (for proctored rounds).",
    )
    proctoringSignals: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional client-side proctoring telemetry (head/eye/tab signals).",
    )


class CodingSubmissionLookupRequest(BaseModel):
    token: str = Field(..., min_length=6, description="Interview token")
    email: EmailStr
