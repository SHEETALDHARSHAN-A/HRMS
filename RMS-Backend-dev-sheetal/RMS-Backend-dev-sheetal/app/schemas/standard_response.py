# app/schemas/standard_response.py

from pydantic import BaseModel
from typing import Optional, List, Any

class StandardResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

    class Config:
        from_attributes = True