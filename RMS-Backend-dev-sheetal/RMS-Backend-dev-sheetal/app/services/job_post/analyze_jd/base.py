# app/services/job_post/analyze_jd/base.py

from typing import List, Dict
from abc import ABC, abstractmethod

class BaseAnalyzeJD(ABC):

    @abstractmethod
    def _get_recommended_skills(self, job_title: str, job_description: str) -> List[Dict[str, any]]:
        return
    
    @abstractmethod
    def analyze_job_details(self, _session_uuid, job_id, job_details):
        """Analyze job details.

        _session_uuid parameter is intentionally prefixed with underscore to
        indicate it may be unused in some implementations and silence static
        analysis warnings.
        """
        return
