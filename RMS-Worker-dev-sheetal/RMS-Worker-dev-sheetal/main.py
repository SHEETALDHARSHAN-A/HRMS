# main.py

import os
import sys
import asyncio
from typing import Dict, List, Set, Optional

# --- Application Imports ---
from src.job_processor import JobProcessor
from src.config.app_config import get_app_config
from src.data_class.job_processor_options import JobProcessorOptions
from src.data_class.job_processor_type import JobProcessorType
from src.processor.resume_processor import ResumeProcessor
from src.db.connection_manager import init_db 

# Import models to ensure they are loaded by SQLAlchemy for init_db
import src.db.models.resume_model
import src.db.models.job_post_model
import src.db.models.curation_model 
import src.db.models.shortlist_model


# NOTE: Console output uses print() as requested (no logging framework).

async def main(): 
    """
    Initializes the database, loads configuration, sets up processors, 
    and starts the job worker loop using direct console printing.
    """
    
    # 1. Initialize Database
    try:
        print("Database initialization starting...")
        # Note: This loads and creates the database schema defined in your models.
        await init_db() 
        print("Database initialization complete.")
    except Exception as e:
        print(f"FATAL: Database initialization failed: {e}")
        sys.exit(1) 

    config = get_app_config()
    # Prefer the configured job_queue from AppConfig (loaded from .env/config files).
    # Fall back to the JOB_QUEUE env var or a safe default if not present in config.
    queue_name = str(getattr(config, "job_queue", None) or os.getenv("JOB_QUEUE") or "resume_queue").strip().strip('"').strip("'")
    if queue_name.lower() in {"", "default_queue", "resume_queued"}:
        print(f"[WARN] Normalizing queue name '{queue_name}' to canonical 'resume_queue'.")
        queue_name = "resume_queue"

    poppler_path = (
        getattr(config, "poppler_path", None)
        or os.getenv("POPPLER_PATH")
        or os.getenv("poppler_path")
        or os.getenv("POPLER_PATH")
        or os.getenv("popler_path")
    )
    if poppler_path:
        poppler_path = str(poppler_path).strip().strip('"').strip("'")
    if poppler_path and poppler_path.lower() in {"none", "null"}:
        poppler_path = None

    # 2. Setup Processors Dictionary
    # ResumeProcessor expects STRINGS for Redis host/port/db in its constructor
    resume_processor = ResumeProcessor(
        redis_port=str(config.redis_port),
        redis_host=config.redis_host,
        redis_db=str(config.redis_db),
        status_channel=config.status_channel,
        job_queue=queue_name,
        llm_api_key=config.effective_groq_api_key,
        poppler_path=poppler_path,
        file_path=config.file_path, 
        config=config 
    )

    processors = {
        JobProcessorType.RESUME_PROCESSOR: resume_processor
    }
        
    # 3. Start Worker
    # JobProcessorOptions expects INTEGERS for Redis port/db 
    worker_options = JobProcessorOptions(
        processors=processors,
        redis_port=config.redis_port,    
        redis_host=config.redis_host,
        redis_db=config.redis_db,       
        job_queue=queue_name,
        worker_set=config.worker_set,
        worker_heartbeat=config.worker_heartbeat
    )

    # Note: The core method in src/job_processor.py has been renamed to 'run'.
    worker = JobProcessor(worker_options)

    print(
        f"\n[WORKER] Starting job processor on queue: {queue_name} "
        f"(config.job_queue={getattr(config, 'job_queue', None)}, poppler_path={poppler_path or 'system-path'})"
    )
    
    await worker.run() 

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"An unexpected error occurred in the main loop: {e}")
        sys.exit(1)