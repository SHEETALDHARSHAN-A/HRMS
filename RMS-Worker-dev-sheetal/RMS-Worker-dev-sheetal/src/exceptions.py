# src/exceptions.py

"""
Custom exception hierarchy for resume processing pipeline.
Enables granular error handling, user-friendly reporting, and proper retry logic.
"""


class ResumeProcessingError(Exception):
    """
    Base class for all file-level resume processing errors.
    These errors are recoverable at the file level (job continues with other files).
    """
    pass


class FileTooLargeError(ResumeProcessingError):
    """
    Raised when uploaded file exceeds the maximum allowed size.
    User should be notified to reduce file size or split documents.
    """
    def __init__(self, filename: str, max_size_mb: int, actual_size_mb: float):
        self.filename = filename
        self.max_size_mb = max_size_mb
        self.actual_size_mb = actual_size_mb
        super().__init__(
            f"File '{filename}' is {actual_size_mb:.2f}MB (max {max_size_mb}MB allowed)"
        )


class DuplicateFileError(ResumeProcessingError):
    """
    Raised when file hash already exists for this job.
    Prevents duplicate processing and database bloat.
    """
    def __init__(self, filename: str, existing_profile_id: str = None):
        self.filename = filename
        self.existing_profile_id = existing_profile_id
        msg = f"Duplicate file '{filename}' - already processed for this job"
        if existing_profile_id:
            msg += f" (existing profile: {existing_profile_id})"
        super().__init__(msg)


class ExtractionTimeoutError(ResumeProcessingError):
    """
    Raised when PDF/DOCX text extraction exceeds timeout limit.
    Indicates corrupted file, malicious payload, or extremely complex document.
    """
    def __init__(self, filename: str, timeout_seconds: int):
        self.filename = filename
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"File '{filename}' extraction timed out after {timeout_seconds}s "
            f"(likely corrupted or too complex)"
        )


class ExtractionContentError(ResumeProcessingError):
    """
    Raised when file parsing fails due to corruption or invalid structure.
    Common causes: password-protected PDFs, malformed DOCX, non-resume files.
    """
    def __init__(self, filename: str, original_error: str):
        self.filename = filename
        self.original_error = original_error
        super().__init__(
            f"File '{filename}' could not be parsed: {original_error}"
        )


class InvalidFileTypeError(ResumeProcessingError):
    """
    Raised when uploaded file is not a resume (e.g., job description, images).
    Implements ML-based content validation.
    """
    def __init__(self, filename: str, detected_type: str = "unknown"):
        self.filename = filename
        self.detected_type = detected_type
        super().__init__(
            f"File '{filename}' is not a valid resume (detected: {detected_type})"
        )


class WorkerFatalError(Exception):
    """
    Raised for system-level failures that require job requeue.
    Examples:
    - Database connection loss
    - Redis unavailability
    - Critical LLM API failures (rate limits, service outage)
    - File system corruption
    
    These errors trigger automatic retry with exponential backoff.
    """
    pass


class PermanentJobFailureError(Exception):
    """
    Raised when a job has exceeded max retry attempts.
    Job will be marked as 'permanently_failed' and moved to dead letter queue.
    """
    def __init__(self, task_id: str, retry_count: int, max_retries: int):
        self.task_id = task_id
        self.retry_count = retry_count
        self.max_retries = max_retries
        super().__init__(
            f"Job {task_id} permanently failed after {retry_count}/{max_retries} retries"
        )