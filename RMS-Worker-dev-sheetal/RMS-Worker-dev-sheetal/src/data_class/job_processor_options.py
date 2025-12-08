# src/data_class/job_processor_options.py

from typing import Dict
from enum import Enum, auto
from pydantic import BaseModel
from src.processor.base import BaseProcessor
from src.data_class.job_processor_type import JobProcessorType

class JobProcessorOptions(BaseModel):
    processors: Dict[JobProcessorType, BaseProcessor]
    redis_port: int  # CHANGED from str to int
    redis_host: str 
    redis_db: int    # CHANGED from str to int
    job_queue: str 
    worker_set: str 
    worker_heartbeat: str 
    
    class Config:
        arbitrary_types_allowed = True