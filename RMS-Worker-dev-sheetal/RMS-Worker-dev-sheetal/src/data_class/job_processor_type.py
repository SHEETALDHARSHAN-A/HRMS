# src/data_class/job_processor_type.py

from enum import Enum

class JobProcessorType(str, Enum):
    """
    Defines the types of jobs that can be processed by the worker.
    """
    
    # Resume processing job (extraction + curation pipeline)
    RESUME_PROCESSOR = "RESUME_PROCESSOR"
    
    def __str__(self) -> str:
        """String representation returns the enum value."""
        return self.value
