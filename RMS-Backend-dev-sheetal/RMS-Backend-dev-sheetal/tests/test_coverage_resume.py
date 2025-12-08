import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from types import SimpleNamespace
from app.services.resume.resume_service import ResumeService

class MockFile:
    def __init__(self, filename):
        self.filename = filename
    async def read(self):
        return b"content"

@pytest.mark.asyncio
async def test_process_resume_upload_job_not_found(fake_db):
    with patch("app.services.resume.resume_service.job_exists", AsyncMock(return_value=False)):
        svc = ResumeService(fake_db)
        res = await svc.process_resume_upload("job1", [])
        assert res["status"] == "failure"
        assert "not found" in res["message"]

@pytest.mark.asyncio
async def test_process_resume_upload_invalid_files(fake_db):
    with patch("app.services.resume.resume_service.job_exists", AsyncMock(return_value=True)):
        # Mock directory creation to avoid disk IO
        with patch.object(Path, "mkdir"):
            files = [MockFile("bad.exe"), MockFile(None)]
            svc = ResumeService(fake_db)
            res = await svc.process_resume_upload("job1", files)
            
            assert res["status"] == "validation_failure"
            assert res["saved_count"] == 0
            assert len(res["skipped_files"]) == 2

@pytest.mark.asyncio
async def test_process_resume_upload_success_with_profile_creation(fake_db):
    with patch("app.services.resume.resume_service.job_exists", AsyncMock(return_value=True)):
        with patch("builtins.open", MagicMock()): # Mock file writing
            with patch.object(Path, "mkdir"):
                # Mock Redis
                mock_redis = AsyncMock()
                with patch("app.services.resume.resume_service.get_redis_client", AsyncMock(return_value=mock_redis)):
                    files = [MockFile("resume.pdf")]
                    form_data = {"applicant_name": "John"}

                    svc = ResumeService(fake_db)
                    # Pass fake_db as the session to create profiles
                    fake_db.add = MagicMock()
                    fake_db.flush = AsyncMock()

                    # Patch Profile to be a lightweight factory that returns a SimpleNamespace
                    with patch("app.services.resume.resume_service.Profile", lambda **kwargs: SimpleNamespace(**kwargs)):
                        res = await svc.process_resume_upload("job1", files, form_metadata=form_data, db=fake_db)

                    assert res["status"] == "success"
                    assert res["saved_count"] == 1
                    # Check if profile was added to DB session
                    assert fake_db.add.called
                    # Check redis queue push
                    mock_redis.lpush.assert_awaited()

@pytest.mark.asyncio
async def test_process_resume_upload_exception_handling(fake_db):
    # Force an exception during job check
    with patch("app.services.resume.resume_service.job_exists", AsyncMock(side_effect=Exception("DB Error"))):
        svc = ResumeService(fake_db)
        res = await svc.process_resume_upload("job1", [])
        assert res["status"] == "failure"
        assert "DB Error" in res["message"]