# app/schemas/analyze_jd_request.py

from pydantic import BaseModel
from typing import List, Optional

class AnalyzeJdRequest(BaseModel):
    job_title: str
    job_description: str
