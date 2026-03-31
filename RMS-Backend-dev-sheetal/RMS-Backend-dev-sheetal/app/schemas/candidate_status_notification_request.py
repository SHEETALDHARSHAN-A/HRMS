from pydantic import BaseModel


class CandidateStatusNotificationRequest(BaseModel):
    profile_id: str
    round_id: str
    result: str
    reason: str | None = None
    source: str | None = None
