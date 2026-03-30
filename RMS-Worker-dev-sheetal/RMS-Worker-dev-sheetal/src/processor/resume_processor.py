# src/processor/resume_processor.py
"""
Production-grade resume processor with comprehensive error handling and user-friendly reporting.

Features:
- Two-phase pipeline (Extraction → Curation)
- User-friendly consolidated summaries
- Granular failure categorization
- Automatic exception re-raising for job requeue
- Real-time WebSocket progress updates
- Async file I/O using asyncio.to_thread
"""

import os
import json
import uuid
import asyncio
import redis.asyncio as redis

from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any
from starlette.datastructures import UploadFile

from .base import BaseProcessor
from src.config.app_config import AppConfig
from src.service.upload_resume import UploadResume
from src.service.curate_profiles import CurateProfiles
from src.db.connection_manager import AsyncSessionLocal

DEFAULT_STATUS_CHANNEL = "ATS_JOB_STATUS" 

class ResumeProcessor(BaseProcessor):
    """
    Worker processor for RESUME_PROCESSOR jobs.
    Orchestrates extraction → curation pipeline with comprehensive error handling.
    """

    def __init__(
        self,
        redis_port: str,
        redis_host: str,
        redis_db: str,
        status_channel: str,
        job_queue: str,
        llm_api_key: str,
        poppler_path: Optional[str] = None,
        file_path: Optional[str] = None,
        config: Optional[AppConfig] = None,
    ):
        """
        Initialize the resume processor.
        """
        self.worker_id = str(uuid.uuid4())
        self.status_channel = status_channel or DEFAULT_STATUS_CHANNEL
        self.llm_api_key = llm_api_key
        self.job_queue = job_queue
        self.poppler_path = poppler_path
        self.config = config or AppConfig()

        # Redis Connection Pool (Async)
        self.redis_pool = redis.ConnectionPool(
            host=redis_host,
            port=int(redis_port),
            db=int(redis_db),
            decode_responses=True,
        )

        # File storage path (from config or fallback)
        self.file_path = Path(
            file_path or
            getattr(self.config, 'file_path', None) or
            os.getenv('FILE_PATH', r'C:\Workspace\resumes')
        ).resolve()

        print(
            f"[INFO] ResumeProcessor initialized: worker_id={self.worker_id}, "
            f"file_path={self.file_path}"
        )

    def get_redis(self) -> redis.Redis:
        """Returns an async Redis client from the connection pool."""
        return redis.Redis(connection_pool=self.redis_pool)

    # ============================================================
    # Progress Publishing (Uses print() for necessary status)
    # ============================================================

    async def publish_progress(
        self,
        redis_client: redis.Redis,
        task_id: str,
        job_id: str,
        file_name: str = "",
        message: str = "",
        stage: str = "processing",
        progress: float = 0.0,
        profile_id: str = "",
    ):
        """
        Publishes structured progress updates to Redis channel/stream and prints critical status.
        """
        payload = {
            "task_id": task_id,
            "job_id": job_id,
            "file_name": file_name,
            "message": message,
            "status": message,
            "profile_id": profile_id,
            "stage": stage,
            "processing_percentage": int(round(progress)),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # ONLY print crucial steps to the console (initial, completion, error, summary)
        if progress in [0, 100] or stage in ["initialization", "completed", "failed", "extraction_summary"]:
             print(
                 f"[PROGRESS] {int(round(progress))}% | {stage} | "
                 f"{file_name or 'job'} | {message}"
             )

        try:
            # Publish to channel (for WebSocket subscribers)
            payload_with_alias = {**payload, "task": task_id}
            await redis_client.publish(
                self.status_channel,
                json.dumps(payload_with_alias)
            )

            # Add to stream (for dashboard persistence and replay)
            try:
                stream_key = f"{self.status_channel}:stream"
                await redis_client.xadd(
                    stream_key,
                    {"payload": json.dumps(payload_with_alias)}
                )
            except Exception as stream_error:
                print(f"[WARN] Stream write failed: {stream_error}")

        except Exception as e:
            print(f"[ERROR] Failed to publish progress: {e}")

    # ============================================================
    # User-Friendly Final Summary
    # ============================================================

    async def publish_final_summary(
        self,
        redis_client: redis.Redis,
        task_id: str,
        job_id: str,
        response: Dict[str, Any],
    ):
        """
        Publishes a consolidated, user-friendly summary after extraction phase.
        """
        success_count = len(response.get("success_files", []))
        
        # Calculate totals
        total_submitted = (
            success_count +
            len(response.get("failed_size_files", [])) +
            len(response.get("failed_duplicate_files", [])) +
            len(response.get("failed_invalid_files", [])) +
            len(response.get("failed_processing_files", []))
        )

        message_parts = []

        # Success Summary
        if success_count > 0:
            message_parts.append(
                f"[SUCCESS] Successfully processed {success_count} out of {total_submitted} resumes."
            )
        else:
            message_parts.append(
                f"[WARN] No resumes were successfully processed out of {total_submitted} submitted."
            )

        # Invalid File Type
        if response.get("failed_invalid_files"):
            names = [f['file_name'] for f in response['failed_invalid_files']]
            types = [f.get('detected_type', 'unknown') for f in response['failed_invalid_files']]
            
            message_parts.append(
                f"\n[FAIL] Invalid file type - Files are not resumes (types: {', '.join(set(types))}): {', '.join(names)}"
            )

        # Duplicate Files
        if response.get("failed_duplicate_files"):
            names = [f['file_name'] for f in response['failed_duplicate_files']]
            message_parts.append(
                f"\n[SKIP] Duplicate resumes detected and skipped (already uploaded for this job): {', '.join(names)}"
            )

        # Size Limit Exceeded
        if response.get("failed_size_files"):
            names = [f['file_name'] for f in response['failed_size_files']]
            message_parts.append(
                f"\n[FAIL] Resume file too large (files > 5MB cannot be processed): {', '.join(names)}"
            )

        # Processing Failures
        if response.get("failed_processing_files"):
            names = [f['file_name'] for f in response['failed_processing_files']]
            message_parts.append(
                f"\n[FAIL] Processing failed (corruption, timeout, or parsing error): {', '.join(names)}"
            )

        final_message = '\n'.join(message_parts) if message_parts else \
                       "[WARN] No valid resumes were processed."

        await self.publish_progress(
            redis_client, task_id, job_id,
            message=final_message,
            stage="extraction_summary",
            progress=50
        )

        print(f"[INFO] Published final summary for job {job_id}: {success_count}/{total_submitted} success")

    # ============================================================
    # File Loading Helper (Robust File I/O)
    # ============================================================

    async def _load_resume_files(
        self,
        job_id: str,
        saved_files_list: Optional[List[str]] = None
    ) -> List[UploadFile]:
        """
        Loads resume files from the file system using async I/O.
        """
        resumes_dir = self.file_path / job_id
        files: List[UploadFile] = []

        # Helper function for blocking file operations
        def _read_file(file_path: Path) -> Optional[bytes]:
            """Synchronous file read (will be run in thread pool)."""
            try:
                if file_path.exists() and file_path.is_file():
                    with open(file_path, "rb") as f:
                        return f.read()
            except Exception as e:
                print(f"[ERROR] Failed to read {file_path.name}: {e}")
            return None

        # Mode 1: Load Specific Files
        if saved_files_list:
            print(f"[INFO] Loading {len(saved_files_list)} specific files from {resumes_dir}")
            
            # Wait for files to appear (edge case: async file system lag tolerance)
            missing = [name for name in saved_files_list if not (resumes_dir / name).exists()]
            if missing:
                print(f"[WARN] Waiting for {len(missing)} files to appear: {missing[:3]}...")
                
                for attempt in range(6):  # 3 seconds total
                    await asyncio.sleep(0.5)
                    missing = [name for name in saved_files_list if not (resumes_dir / name).exists()]
                    if not missing:
                        print("[INFO] All files now present")
                        break
                else:
                    print(f"[ERROR] Files still missing after wait: {missing}")

            # Load files asynchronously
            for file_name in saved_files_list:
                file_path = resumes_dir / file_name
                content = await asyncio.to_thread(_read_file, file_path)
                
                if content:
                    files.append(
                        UploadFile(filename=file_name, file=BytesIO(content))
                    )
                else:
                    print(f"[WARN] File not found or not readable: {file_path}")

        # Mode 2: Scan Directory
        else:
            if not resumes_dir.exists():
                raise FileNotFoundError(f"Resume directory not found: {resumes_dir}")

            print(f"[INFO] Scanning directory for resume files: {resumes_dir}")
            
            file_names = await asyncio.to_thread(lambda: os.listdir(resumes_dir))
            
            for file_name in file_names:
                file_path = resumes_dir / file_name
                content = await asyncio.to_thread(_read_file, file_path)
                
                if content:
                    files.append(
                        UploadFile(filename=file_name, file=BytesIO(content))
                    )

        if not files:
            raise FileNotFoundError(f"No resume files found in {resumes_dir}")

        print(f"[INFO] Successfully loaded {len(files)} resume files")
        return files

    # ============================================================
    # Main Job Processing Logic
    # ============================================================

    async def invoke(self, job: Dict) -> Optional[Dict]:
        """
        Main entrypoint for RESUME_PROCESSOR jobs.
        """
        job_id = job.get("job_id")
        task_id = job.get("task_id")
        process_type = job.get("process_type")

        # Validate Job Payload (Edge case handling)
        if process_type != "RESUME_PROCESSOR" or not job_id or not task_id:
            print(f"[ERROR] Invalid job payload: {job}")
            return None

        # ASCII Worker/Job Information Banner
        print("\n" + "="*50)
        print(f"JOB START: {job_id}")
        print(f"TASK ID: {task_id}")
        print(f"WORKER: {self.worker_id}")
        print("="*50)

        redis_client = self.get_redis()

        # Create fresh database session for this job
        async with AsyncSessionLocal() as db_session:
            # Initialize services
            resume_service = UploadResume(
                db_session=db_session,
                redis_store=redis_client,
                config=self.config
            )
            curation_service = CurateProfiles(db_session=db_session)

            try:
                # INITIALIZE JOB STATE
                job["status"] = "processing"
                job["updated_at"] = datetime.utcnow().isoformat()
                await redis_client.hset(f"job:{task_id}", mapping=job)

                await self.publish_progress(
                    redis_client, task_id, job_id,
                    message="Job initialized. Starting file extraction (Phase 1/2).",
                    stage="initialization",
                    progress=0
                )

                # LOAD RESUME FILES
                
                saved_files_list: List[str] = []
                try:
                    raw_saved = job.get("saved_files")
                    if raw_saved:
                        saved_files_list = (
                            json.loads(raw_saved) if isinstance(raw_saved, str) else list(raw_saved)
                        )
                except Exception as e:
                    print(f"[WARN] Failed to parse saved_files: {e}")

                files = await self._load_resume_files(job_id, saved_files_list)
                total_files = len(files)
                
                # PHASE 1: RESUME EXTRACTION
                print(f"[INFO] Starting Phase 1: Resume Extraction ({total_files} files)")

                # Extract form metadata if present
                form_metadata = None
                if "form_metadata" in job:
                    try:
                        form_metadata = (
                            json.loads(job["form_metadata"])
                            if isinstance(job["form_metadata"], str)
                            else job["form_metadata"]
                        )
                        print(f"[INFO] Using career application form data: {form_metadata}")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"[WARN] Failed to parse form_metadata: {e}")

                # Execute extraction (Robust step)
                resume_response = await resume_service.upload_resumes(
                    job_id=job_id,
                    files=files,
                    redis_client=redis_client,
                    task_id=task_id,
                    resume_processor=self,
                    status_channel=self.status_channel,
                    form_metadata=form_metadata,
                )

                # Publish user-friendly summary (Modification 2 starts here)
                await self.publish_final_summary(
                    redis_client, task_id, job_id, resume_response
                )

                # Check Extraction Results (Edge case: no successful files)
                success_files = resume_response.get("success_files")

                if not success_files:
                    print(f"[WARN] No valid resumes extracted for job {job_id}")
                    
                    # Build detailed failure summary
                    failure_summary = []
                    if resume_response.get("failed_invalid_files"):
                        invalid_count = len(resume_response["failed_invalid_files"])
                        failure_summary.append(f"{invalid_count} invalid file(s) (not resumes)")
                    if resume_response.get("failed_duplicate_files"):
                        dup_count = len(resume_response["failed_duplicate_files"])
                        failure_summary.append(f"{dup_count} duplicate(s)")
                    if resume_response.get("failed_size_files"):
                        size_count = len(resume_response["failed_size_files"])
                        failure_summary.append(f"{size_count} oversized file(s)")
                    if resume_response.get("failed_processing_files"):
                        proc_count = len(resume_response["failed_processing_files"])
                        failure_summary.append(f"{proc_count} processing error(s)")
                    
                    summary_msg = "No valid resumes processed. " + ", ".join(failure_summary) if failure_summary else "No files were submitted."
                    
                    await self.publish_progress(
                        redis_client, task_id, job_id,
                        message=summary_msg,
                        stage="completed",
                        progress=100
                    )

                    job["status"] = "completed"
                    job["completion_note"] = "no_valid_resumes"
                    job["updated_at"] = datetime.utcnow().isoformat()
                    await redis_client.hset(f"job:{task_id}", mapping=job)

                    print(f"[INFO] Job {job_id} completed with no valid resumes")
                    
                    return {
                        "success": True,
                        "job_id": job_id,
                        "task_id": task_id,
                        "note": "no_valid_resumes",
                        "details": resume_response
                    }

                # PHASE 2: CURATION
                print(f"[INFO] Starting Phase 2: Curation ({len(success_files)} profiles)")

                await self.publish_progress(
                    redis_client, task_id, job_id,
                    message=f"Extraction complete. {len(success_files)} profiles ready for curation (Phase 2/2).",
                    stage="curation_preparation",
                    progress=50
                )

                profile_ids = [p["profile_id"] for p in success_files]
                total_profiles = len(profile_ids)

                await self.publish_progress(
                    redis_client, task_id, job_id,
                    message=f"Starting LLM curation for {total_profiles} profiles...",
                    stage="curation_in_progress",
                    progress=50
                )

                # Execute curation (Robust step)
                curation_response = await curation_service.process_curation_logic(
                    job_id=job_id,
                    task_id=task_id,
                    profile_ids=profile_ids,
                    redis_client=redis_client,
                    status_channel=self.status_channel,
                )

                if not (curation_response and curation_response.get("success")):
                    raise RuntimeError(
                        curation_response.get("message", "Curation phase failed")
                    )

                # FINALIZE JOB
                await self.publish_progress(
                    redis_client, task_id, job_id,
                    message="Pipeline execution complete. Results saved successfully.",
                    stage="completed",
                    progress=100
                )

                job["status"] = "completed"
                job["updated_at"] = datetime.utcnow().isoformat()
                await redis_client.hset(f"job:{task_id}", mapping=job)

                print("\n" + "="*50)
                print(f"[SUCCESS] Job Completed Successfully: {job_id}")
                print(f"[INFO] Profiles Processed: {total_profiles}")
                print("="*50)

                return {
                    "success": True,
                    "job_id": job_id,
                    "task_id": task_id
                }

            except Exception as e:
                # CRITICAL ERROR HANDLING
                error_msg = f"{type(e).__name__}: {e}"
                print("\n" + "="*50)
                print(f"[CRITICAL] ERROR - Job Failed: {job_id}")
                print(f"[ERROR] Task ID: {task_id}")
                print(f"[ERROR] Error: {error_msg}")
                print("="*50)

                # Update job status in Redis
                job["status"] = "failed"
                job["error_message"] = error_msg
                job["updated_at"] = datetime.utcnow().isoformat()
                await redis_client.hset(f"job:{task_id}", mapping=job)

                # User-friendly failure message
                await self.publish_progress(
                    redis_client, task_id, job_id,
                    message="Worker failed unexpectedly. The system will automatically retry this job.",
                    stage="failed",
                    progress=100
                )

                # RE-RAISE: Critical for job requeue
                raise

            finally:
                await redis_client.close()
