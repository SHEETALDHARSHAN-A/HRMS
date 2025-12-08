# app/services/resume/resume_service.py

import uuid
import json
import logging
import hashlib

from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
from typing import List, Dict, Any

from app.db.redis_manager import get_redis_client
from app.db.repository.job_post_repository import job_exists 
from app.db.models.resume_model import Profile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

UPLOAD_BASE_PATH = Path(r"C:\Workspace\resumes")

class ResumeService:
    """Handle resume upload and queueing, allowing partial success."""

    def __init__(self, db=None):
        self.db = db
        self.upload_dir_base = UPLOAD_BASE_PATH

    async def process_resume_upload(self, job_id: str, files: List[UploadFile], form_metadata: Dict[str, Any] = None, db: AsyncSession = None) -> Dict[str, Any]:
        """
        Processes files, allowing partial success.
        If `form_metadata` and `db`/self.db are provided, create initial Profile
        records using the form values (name/email/phone) and the saved filename
        so resume extraction can later enrich the same profile record.
        Returns a dictionary containing the detailed outcome.
        """
        result = {
            'status': 'failure', 
            'saved_count': 0, 
            'skipped_files': [], 
            'message': 'Unable to upload resumes due to an internal error.'
        }
        
        try:
            # 1. Check job existence
            if not await job_exists(self.db, job_id):
                result['message'] = f"Job ID '{job_id}' not found in database."
                logger.warning(f"[ResumeService] {result['message']}")
                return result

            save_dir = self.upload_dir_base / job_id
            save_dir.mkdir(parents=True, exist_ok=True)

            saved_files_list = []
            skipped_files_list = []
            # Map filename -> sha256 hash for duplicate detection/linking
            saved_file_hashes: Dict[str, str] = {}

            # 2. Process all files (allowing skips)
            for file in files:
                filename = file.filename
                
                # Validation check for PDF/DOCX format and existence
                if not filename or not filename.lower().endswith((".pdf", ".docx")):
                    skipped_files_list.append(filename or 'unnamed_file - Invalid Format')
                    continue 
                
                content = await file.read()
                if not content:
                    skipped_files_list.append(f"{filename} - Empty File")
                    continue
                # Compute file hash for duplicate detection and linking
                try:
                    file_hash = hashlib.sha256(content).hexdigest()
                except Exception:
                    file_hash = None
                    
                # Save valid file
                file_path = save_dir / filename
                with open(file_path, "wb") as f:
                    f.write(content)
                saved_files_list.append(filename)
                if file_hash:
                    saved_file_hashes[filename] = file_hash
            
            # Update results after processing files
            result['saved_count'] = len(saved_files_list)
            result['skipped_files'] = skipped_files_list

            # 3. Queue only if valid files were saved
            if result['saved_count'] > 0:
                # If caller provided a DB session (or the service was constructed
                # with one), create Profile rows for each saved file using
                # the supplied form metadata so that extraction can be linked
                # to these profiles.
                use_db = db or self.db
                created_profiles = []
                if use_db is not None and form_metadata:
                    try:
                        # form_metadata expected keys: applicant_name, applicant_email, applicant_phone
                        applicant_name = form_metadata.get("applicant_name", "")
                        applicant_email = form_metadata.get("applicant_email", "")
                        applicant_phone = form_metadata.get("applicant_phone", "")
                        # Create one profile per saved file so each resume file is represented
                        # in the profiles table. Instead of starting a nested transaction
                        # (which may already exist on the provided session), add instances
                        # to the session and flush so DB gets assigned primary keys.
                        for fname in saved_files_list:
                            profile = Profile(
                                job_id=job_id,
                                name=applicant_name or fname,
                                email=applicant_email or "",
                                phone_number=applicant_phone or "",
                                file_name=fname,
                                file_type=(Path(fname).suffix.lstrip('.') or ""),
                                file_hash=saved_file_hashes.get(fname),
                                resume_link=str((self.upload_dir_base / job_id / fname).as_posix()),
                                extracted_content={},
                            )
                            use_db.add(profile)
                            created_profiles.append(profile)

                        # Flush to send INSERTs to DB and populate PKs without committing
                        try:
                            await use_db.flush()
                        except Exception:
                            # Non-fatal: log and continue — resume processing should still proceed
                            logger.exception("[ResumeService] Failed to flush created profile records.")
                    except Exception as e:
                        logger.exception("[ResumeService] Failed to create initial profile records: %s", e)

                redis_client = await get_redis_client()
                task_id = str(uuid.uuid4())
                now_iso = datetime.utcnow().isoformat()
                
                job_data = {
                    "task_id": task_id,
                    "job_id": job_id,
                    "process_type": "RESUME_PROCESSOR",
                    "status": "pending_processing", 
                    "created_at": now_iso,
                    "updated_at": now_iso,
                    "error_message": "",
                    "saved_files": json.dumps(saved_files_list), 
                }

                if form_metadata:
                    try:
                        job_data["form_metadata"] = json.dumps(form_metadata, ensure_ascii=False)
                    except Exception:
                        job_data["form_metadata"] = str(form_metadata)
                if created_profiles:
                    try:
                        job_data["created_profiles"] = json.dumps(
                            [ {"file_name": p.file_name, "email": p.email, "file_hash": getattr(p, 'file_hash', None)} for p in created_profiles ],
                            ensure_ascii=False
                        )
                    except Exception:
                        job_data["created_profiles"] = str([getattr(p, 'file_name', None) for p in created_profiles])

                await redis_client.hset(f"job:{task_id}", mapping=job_data)
                await redis_client.lpush("resume_queue", task_id)
                await redis_client.close()
                
                result['status'] = 'success'
                # Expose the generated task_id and saved files to the caller
                result['task_id'] = task_id
                result['saved_files'] = saved_files_list
                if created_profiles:
                    # Try to extract created profile ids if available (SQLAlchemy will
                    # populate them after commit). We include placeholder info so callers
                    # can link processing to created profiles where possible.
                    try:
                        result['created_profiles'] = [ { 'file_name': p.file_name, 'email': p.email } for p in created_profiles ]
                    except Exception:
                        # Non-critical; ignore
                        pass
                result['message'] = 'Upload and queuing process initiated.'
                logger.info(f"[ResumeService] Successfully processed {result['saved_count']} and skipped {len(skipped_files_list)} files.")
                return result
            
            else:
                # Case: 0 files were saved (all were invalid/skipped)
                result['status'] = 'validation_failure'
                result['message'] = "No valid files were uploaded. All files were skipped due to format or size issues."
                return result

        except Exception as e:
            error_msg = f"Failed to process upload due to unexpected internal server error: {str(e)}"
            logger.error(f"[ResumeService] {error_msg}", exc_info=True)
            result['message'] = error_msg
            result['status'] = 'failure'
            return result