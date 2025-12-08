# src/service/upload_resume.py

import os
import re
import uuid
import json
import asyncio

from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import TimeoutError as ConcurrentTimeoutError

import fitz  # PyMuPDF
from docx import Document
from starlette.datastructures import UploadFile

# Agents & DB
from agents import Agent, Runner
from sqlalchemy.ext.asyncio import AsyncSession

# Redis
import redis.asyncio as redis

# Internal imports
from src.config.app_config import AppConfig
from src.utils.hash_file import compute_hash
from src.db.repository.resume_repository import ResumeRepository
from src.prompts.resume_extraction_prompt import RESUME_EXTRACTION_PROMPT
from src.exceptions import (
    FileTooLargeError,
    DuplicateFileError,
    ExtractionTimeoutError,
    ExtractionContentError,
    InvalidFileTypeError,
)


# Configuration constants
EXTRACTION_TIMEOUT_SECONDS = 30
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class UploadResume:
    """
    Service for processing resume uploads with extraction, validation, and caching.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        redis_store: redis.Redis,
        config: Optional[AppConfig] = None,
    ):
        """
        Initialize the UploadResume service.
        """
        self.db_session = db_session
        self.resume_repo = ResumeRepository(db_session)
        self.redis_store = redis_store
        self.config = config or AppConfig()
        
        # File size limits
        self.max_file_size = MAX_FILE_SIZE_BYTES
        self.max_file_size_mb = MAX_FILE_SIZE_MB

        # Poppler path for PDF processing
        self.poppler_path = getattr(self.config, 'poppler_path', None) or \
                           os.getenv('POPPLER_PATH')
        
        print(
            f"[INFO] UploadResume initialized: max_size={self.max_file_size_mb}MB, "
            f"timeout={EXTRACTION_TIMEOUT_SECONDS}s"
        )

    # ============================================================
    # Agent Creation
    # ============================================================

    def create_resume_extraction_agent(self) -> Agent:
        """Creates the multilingual resume extraction agent with validation."""
        return Agent(
            name="Multilingual Resume Extractor",
            instructions=RESUME_EXTRACTION_PROMPT
        )

    # ============================================================
    # Text Extraction Methods (Sync - will be run in thread pool)
    # ============================================================

    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extract text from PDF file using PyMuPDF.
        """
        text = ""
        try:
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                for page_num, page in enumerate(doc, start=1):
                    try:
                        page_text = page.get_text("text")
                        text += page_text
                    except Exception as page_error:
                        print(f"[WARN] Failed to extract page {page_num}: {page_error}")
                        continue
            
            if not text.strip():
                raise ValueError("PDF contains no extractable text (might be scanned image)")
                
            return text.strip()
            
        except fitz.FileDataError as e:
            raise ValueError(f"Corrupted or invalid PDF file: {e}")
        except Exception as e:
            raise ValueError(f"PDF extraction failed: {e}")

    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """
        Extract text from DOCX file using python-docx.
        """
        try:
            doc = Document(BytesIO(file_content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            
            if not paragraphs:
                raise ValueError("DOCX contains no readable text")
            
            return "\n".join(paragraphs).strip()
            
        except Exception as e:
            raise ValueError(f"DOCX extraction failed: {e}")

    # ============================================================
    # Timeout-Protected Extraction (Async wrapper)
    # ============================================================

    async def _extract_text_with_timeout(
        self,
        file_content: bytes,
        file_type: str,
        file_name: str
    ) -> str:
        """
        Wraps synchronous text extraction with async timeout protection.
        """
        try:
            if file_type == "pdf":
                text = await asyncio.wait_for(
                    asyncio.to_thread(self._extract_text_from_pdf, file_content),
                    timeout=EXTRACTION_TIMEOUT_SECONDS
                )
            elif file_type == "docx":
                text = await asyncio.wait_for(
                    asyncio.to_thread(self._extract_text_from_docx, file_content),
                    timeout=EXTRACTION_TIMEOUT_SECONDS
                )
            else:
                raise ExtractionContentError(
                    file_name,
                    f"Unsupported file type: {file_type}"
                )

            if not text or len(text.strip()) < 50:
                raise ExtractionContentError(
                    file_name,
                    "File contains insufficient text content (less than 50 characters)"
                )

            return text.strip()

        except (asyncio.TimeoutError, ConcurrentTimeoutError):
            print(f"[ERROR] Extraction timeout for {file_name} after {EXTRACTION_TIMEOUT_SECONDS}s")
            raise ExtractionTimeoutError(file_name, EXTRACTION_TIMEOUT_SECONDS)

        except ExtractionContentError:
            raise

        except Exception as e:
            print(f"[ERROR] Extraction error for {file_name}: {type(e).__name__} - {e}")
            raise ExtractionContentError(file_name, str(e))

    # ============================================================
    # LLM-Based Resume Extraction with Validation
    # ============================================================

    async def extract_resume(
        self,
        file_content: bytes,
        file_type: str,
        file_hash: str,
        file_name: str
    ) -> Dict[str, Any]:
        """
        Extracts structured resume data using LLM with content validation.
        """
        # Check Redis Cache
        if self.redis_store:
            try:
                cached_data = await self.redis_store.hgetall(file_hash)
                if cached_data:
                    print(f"[INFO] [CACHE HIT] {file_name} (hash: {file_hash[:8]}...)")
                    
                    cached_content = cached_data.get(b"extracted_content") or \
                                   cached_data.get("extracted_content")
                    
                    if cached_content:
                        if isinstance(cached_content, bytes):
                            cached_content = cached_content.decode("utf-8")
                        
                        try:
                            extracted_data = json.loads(cached_content)
                            
                            # Validate cached data
                            if extracted_data.get("is_valid_resume") is False:
                                raise InvalidFileTypeError(
                                    file_name,
                                    extracted_data.get("detected_type", "unknown")
                                )
                            
                            return extracted_data
                            
                        except json.JSONDecodeError as e:
                            print(f"[WARN] [CACHE ERROR] Invalid JSON for {file_name}, re-extracting")
                            
            except Exception as e:
                print(f"[WARN] [CACHE ERROR] Redis read failed for {file_name}: {e}")

        # Extract Text with Timeout
        print(f"[INFO] [CACHE MISS] Extracting {file_name} via LLM")
        
        text = await self._extract_text_with_timeout(file_content, file_type, file_name)

        # LLM Extraction with Validation
        agent = self.create_resume_extraction_agent()
        
        try:
            result = await Runner.run(agent, [
                {
                    "role": "user",
                    "content": f"Extract structured resume information:\n\n{text}"
                }
            ])
            
            # Robust JSON parsing (Edge Case: LLM output is wrapped in markdown)
            json_match = re.search(r'```(?:jsonc?|)\n(.*)```', result.final_output, re.DOTALL)
            json_string = json_match.group(1).strip() if json_match else result.final_output.strip()
            
            extracted_data = json.loads(json_string)
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] [LLM ERROR] Invalid JSON output for {file_name}: {e}")
            
            # Assigning Invalid/Non-Resume data structure (Edge Case)
            extracted_data = {
                "is_valid_resume": False,
                "detected_type": "parsing_error",
                "confidence": 0.0,
                "reason": f"LLM output parsing failed: {e}"
            }
        
        except Exception as e:
            print(f"[ERROR] [LLM ERROR] Extraction failed for {file_name}: {e}")
            raise ExtractionContentError(file_name, f"LLM extraction failed: {e}")

        # Validate Document Type (CRITICAL EDGE CASE: JD Rejection)
        if extracted_data.get("is_valid_resume") is False:
            detected_type = extracted_data.get("detected_type", "unknown")
            reason = extracted_data.get("reason", "Document is not a resume")
            confidence = extracted_data.get("confidence", 0.0)
            
            print(
                f"[WARN] [INVALID FILE] {file_name} rejected - Type: {detected_type} "
                f"(Confidence: {confidence:.1%}) | Reason: {reason}"
            )
            
            # Cache the invalid result to prevent re-processing
            if self.redis_store:
                try:
                    await self.redis_store.hset(
                        file_hash,
                        mapping={
                            "file_name": file_name,
                            "extracted_content": json.dumps(extracted_data, ensure_ascii=False),
                            "timestamp": datetime.now().isoformat(),
                            "is_valid": "false",
                            "detected_type": detected_type,
                            "rejection_reason": reason
                        }
                    )
                    # Set expiry for invalid file cache (7 days = 604800 seconds)
                    await self.redis_store.expire(file_hash, 604800)
                    print(f"[INFO] [CACHE WRITE] Cached rejection for {file_name}")
                except Exception as e:
                    print(f"[WARN] [CACHE ERROR] Failed to cache invalid file: {e}")
            
            # This exception is caught in upload_resumes, which adds it to failed_invalid_files
            # and prevents it from being added to the database.
            raise InvalidFileTypeError(file_name, detected_type)

        # Cache Valid Result
        if self.redis_store:
            try:
                hash_data = {
                    "file_name": file_name,
                    "extracted_content": json.dumps(extracted_data, ensure_ascii=False),
                    "timestamp": datetime.now().isoformat(),
                    "is_valid": "true"
                }
                
                await self.redis_store.hset(file_hash, mapping=hash_data)
                print(f"[INFO] [CACHE WRITE] Stored extraction for {file_name}")
                
            except Exception as e:
                print(f"[WARN] [CACHE ERROR] Write failed for {file_name}: {e}")

        return extracted_data

    # ============================================================
    # Batch Resume Upload with Granular Error Handling
    # ============================================================

    async def upload_resumes(
        self,
        job_id: str,
        files: List[UploadFile],
        redis_client: redis.Redis,
        status_channel: str,
        task_id: str,
        resume_processor,
        form_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process batch resume upload with comprehensive error handling.
        """
        # Ensure fresh transaction view
        await self.db_session.rollback()

        # Validate job_id format (Edge case)
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError as e:
            print(f"[ERROR] Invalid job_id format: {job_id}")
            raise ValueError(f"Invalid job_id format: {job_id}") from e

        # Initialize Processing State
        existing_hashes = await self.resume_repo.get_existing_hashes_for_job(job_uuid)
        
        # Result categorization lists
        success_files = []
        failed_size_files = []
        failed_duplicate_files = []
        failed_invalid_files = []
        failed_processing_files = []
        
        total_files = len(files)
        file_data_list = []

        # Log processing mode
        is_career_app = form_metadata and form_metadata.get("source") == "career_application"
        if is_career_app:
            print(
                f"[INFO] [CAREER APP MODE] Processing {total_files} files with form data: "
                f"{form_metadata.get('applicant_name', 'N/A')}"
            )
        else:
            print(f"[INFO] [BULK UPLOAD MODE] Processing {total_files} files")

        # Process Each File
        files_processed = 0
        for file in files:
            files_processed += 1
            progress = int((files_processed / total_files) * 50)
            profile_id_placeholder = "N/A"

            # Publish start message
            await resume_processor.publish_progress(
                redis_client, task_id, job_id, file.filename,
                f"[STATUS] Processing {file.filename}...",
                "processing", progress=progress, profile_id=profile_id_placeholder
            )

            try:
                # Read File Content
                content = await file.read()
                actual_size_mb = len(content) / (1024 * 1024)
                
                # Size Validation (Edge case)
                if len(content) > self.max_file_size:
                    raise FileTooLargeError(file.filename, self.max_file_size_mb, actual_size_mb)

                # Duplicate Detection (Edge case)
                file_hash = compute_hash(content)
                if file_hash in existing_hashes:
                    existing_profile_id = existing_hashes.get(file_hash, "unknown")
                    raise DuplicateFileError(file.filename, existing_profile_id)

                # File Type Detection (Edge case)
                filename_lower = file.filename.lower()
                if filename_lower.endswith(".pdf"):
                    file_type = "pdf"
                elif filename_lower.endswith(".docx"):
                    file_type = "docx"
                else:
                    raise ExtractionContentError(
                        file.filename, f"Unsupported file extension (only .pdf and .docx allowed)"
                    )

                # Extract & Validate Resume Content (Robust step)
                extracted_data = await self.extract_resume(content, file_type, file_hash, file.filename)

                # Determine Profile Data Source (Edge case: form data override)
                if is_career_app:
                    profile_name = (
                        form_metadata.get("applicant_name") or extracted_data.get("name") or "Unknown Applicant"
                    )
                    profile_email = (
                        form_metadata.get("applicant_email") or extracted_data.get("email") or ""
                    )
                    profile_phone = (
                        form_metadata.get("applicant_phone") or extracted_data.get("phone") or ""
                    )
                else:
                    profile_name = extracted_data.get("name") or "Unknown"
                    profile_email = extracted_data.get("email") or ""
                    profile_phone = extracted_data.get("phone") or ""
                    
                    if not profile_email or not profile_phone:
                        print(f"[WARN] LLM extraction incomplete for {file.filename}: email={bool(profile_email)}, phone={bool(profile_phone)}")

                # Prepare for Bulk Insert
                file_data_list.append({
                    "job_id": job_uuid,
                    "name": profile_name,
                    "email": profile_email,
                    "phone": profile_phone,
                    "location": extracted_data.get("location"),
                    "extracted_content": extracted_data,
                    "file_name": file.filename,
                    "file_type": file_type,
                    "file_hash": file_hash,
                })

                # Mark this hash as processed
                existing_hashes[file_hash] = "pending"

                # Publish success
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[SUCCESS] Extracted successfully",
                    "processed", progress=progress, profile_id=profile_id_placeholder
                )

                print(f"[INFO] Successfully processed {file.filename}")

            # Exception Handling by Category (Filters Invalid Files)
            except FileTooLargeError as e:
                failed_size_files.append({"file_name": file.filename, "message": str(e), "size_mb": e.actual_size_mb})
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[FAIL] File too large ({e.actual_size_mb:.1f}MB > {e.max_size_mb}MB)",
                    "failed_size", progress=progress, profile_id=profile_id_placeholder
                )

            except DuplicateFileError as e:
                failed_duplicate_files.append({
                    "file_name": file.filename, "message": str(e), "existing_profile_id": e.existing_profile_id
                })
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[SKIP] Duplicate (already uploaded for profile {e.existing_profile_id})",
                    "failed_duplicate", progress=progress, profile_id=profile_id_placeholder
                )
                print(f"[INFO] Duplicate detected: {file.filename}")

            except InvalidFileTypeError as e:
                failed_invalid_files.append({
                    "file_name": file.filename, "message": str(e), "detected_type": e.detected_type
                })
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[FAIL] Not a resume (detected: {e.detected_type})",
                    "failed_invalid", progress=progress, profile_id=profile_id_placeholder
                )
                print(f"[WARN] Invalid file type: {file.filename} -> {e.detected_type}")

            except ExtractionTimeoutError as e:
                failed_processing_files.append({"file_name": file.filename, "message": str(e), "error_type": "timeout"})
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[FAIL] Processing timeout (file too complex/corrupted)",
                    "failed_timeout", progress=progress, profile_id=profile_id_placeholder
                )
                print(f"[ERROR] Timeout: {file.filename}")

            except ExtractionContentError as e:
                failed_processing_files.append({"file_name": file.filename, "message": str(e), "error_type": "corruption"})
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[FAIL] File corrupted or malformed",
                    "failed_corruption", progress=progress, profile_id=profile_id_placeholder
                )
                print(f"[ERROR] Corruption: {file.filename} - {e.original_error}")

            except Exception as e:
                # Catch-all for unexpected errors
                failed_processing_files.append({"file_name": file.filename, "message": f"{type(e).__name__}: {str(e)}", "error_type": "unknown"})
                await resume_processor.publish_progress(
                    redis_client, task_id, job_id, file.filename,
                    f"[FAIL] Unexpected error: {type(e).__name__}",
                    "failed_unknown", progress=progress, profile_id=profile_id_placeholder
                )
                print(f"[ERROR] Unexpected error for {file.filename}: {type(e).__name__} - {e}")

        # Bulk Database Insert (Atomic step)
        if file_data_list:
            try:
                print(f"[INFO] Inserting {len(file_data_list)} profiles into database...")
                created_profiles = await self.resume_repo.create_resumes(file_data_list)
                
                for profile in created_profiles:
                    success_files.append({"file_name": profile.file_name, "profile_id": str(profile.id)})
                
                print(f"[INFO] Successfully inserted {len(success_files)} profiles")
                
            except Exception as e:
                print(f"[ERROR] [DB ERROR] Bulk insert failed: {e}")
                await self.db_session.rollback()
                
                # Move all pending files to failed processing (Edge case: DB failure)
                for file_data in file_data_list:
                    failed_processing_files.append({
                        "file_name": file_data["file_name"],
                        "message": f"Database insertion failed: {e}",
                        "error_type": "database"
                    })
        else:
            await self.db_session.rollback()
            print("[INFO] No files to insert into database")

        # Return Categorized Results
        result = {
            "status_code": 200,
            "success": bool(success_files),
            "message": (
                f"Uploaded {len(success_files)}/{total_files} files successfully" if success_files else "All files failed processing"
            ),
            "success_files": success_files,
            "failed_size_files": failed_size_files,
            "failed_duplicate_files": failed_duplicate_files,
            "failed_invalid_files": failed_invalid_files,
            "failed_processing_files": failed_processing_files,
        }

        print(
            f"[INFO] Upload complete: {len(success_files)} success, "
            f"{len(failed_size_files)} too large, "
            f"{len(failed_duplicate_files)} duplicates, "
            f"{len(failed_invalid_files)} invalid type, "
            f"{len(failed_processing_files)} processing errors"
        )

        return result
