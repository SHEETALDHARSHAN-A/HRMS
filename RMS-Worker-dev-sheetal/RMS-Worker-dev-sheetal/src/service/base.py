from abc import ABC, abstractmethod
from typing import List

class BaseUploadResume(ABC):

    @abstractmethod
    def get_base64_content(self, file_content: bytes, file_type: str) -> str:
        """Convert a file's bytes into base64 string."""
        pass

    @abstractmethod
    async def upload_resumes_details(self, job_id: str, files: List, redis_client, status_channel, task_id, resume_processor):
        """Process and store resumes, publish progress to Redis."""
        pass

    @abstractmethod
    async def extract_resume_from_file(self, file_content: bytes, file_type: str) -> str:
        """Extract structured resume details from a file."""
        pass

    @abstractmethod
    def create_resume_extraction_agent(self):
        """Return an agent capable of extracting resume information."""
        pass
