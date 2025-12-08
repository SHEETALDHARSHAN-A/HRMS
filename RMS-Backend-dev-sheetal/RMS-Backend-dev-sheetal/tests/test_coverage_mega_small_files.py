"""
COMPREHENSIVE TEST FILE: Small Files & Controllers
Covers: agent_config_routes, resume_controller, public_search_service,
        job_post_permissions, update_jd_request, analyze_jd/base, upload_jd/base,
        career_application_service, agent_config_service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status, UploadFile
from typing import List
from io import BytesIO

# =================================================================================================
# agent_config_routes.py (94%, 35 lines) - Controller Wrapper
# =================================================================================================

@pytest.mark.asyncio
async def test_agent_config_route_success():
    """Test agent_config_route success path"""
    from app.controllers.agent_config_routes import update_agent_config_route
    
    mock_db = AsyncMock()
    mock_result = {"success": True, "data": "updated"}
    
    with patch('app.controllers.agent_config_routes._update_agent_config_route', return_value=mock_result):
        result = await update_agent_config_route("job1", MagicMock(), MagicMock(), mock_db)
        assert result == mock_result


@pytest.mark.asyncio
async def test_agent_config_route_failure():
    """Test agent_config_route failure path (raises HTTPException)"""
    from app.controllers.agent_config_routes import update_agent_config_route
    
    mock_db = AsyncMock()
    mock_result = {"success": False, "status_code": 400, "message": "Bad Request"}
    
    with patch('app.controllers.agent_config_routes._update_agent_config_route', return_value=mock_result):
        with pytest.raises(HTTPException) as exc_info:
            await update_agent_config_route("job1", MagicMock(), MagicMock(), mock_db)
        
        assert exc_info.value.status_code == 400


# =================================================================================================
# resume_controller.py (67%, 124 lines) - Controller
# =================================================================================================

@pytest.mark.asyncio
async def test_resume_controller_success():
    """Test resume_controller success path"""
    from app.controllers.resume_controller import upload_resumes_controller
    
    mock_db = AsyncMock()
    mock_files = [UploadFile(file=BytesIO(b""), filename="test.pdf")]
    
    with patch('app.controllers.resume_controller.ResumeService') as MockService:
        mock_instance = MockService.return_value
        mock_instance.process_resume_upload.return_value = {
            'status': 'success',
            'saved_count': 1,
            'skipped_files': [],
            'saved_files': ['test.pdf'],
            'task_id': 'task1'
        }
        
        result = await upload_resumes_controller("job1", mock_files, mock_db)
        assert result['status_code'] == 202


@pytest.mark.asyncio
async def test_resume_controller_partial_success():
    """Test resume_controller partial success"""
    from app.controllers.resume_controller import upload_resumes_controller
    
    mock_db = AsyncMock()
    mock_files = [UploadFile(file=BytesIO(b""), filename="valid.pdf"), UploadFile(file=BytesIO(b""), filename="invalid.txt")]
    
    with patch('app.controllers.resume_controller.ResumeService') as MockService:
        mock_instance = MockService.return_value
        mock_instance.process_resume_upload.return_value = {
            'status': 'partial_success',
            'saved_count': 1,
            'skipped_files': ['invalid.txt'],
            'saved_files': ['valid.pdf']
        }
        
        result = await upload_resumes_controller("job1", mock_files, mock_db)
        assert result['status_code'] == 202
        assert "skipped" in result['message']


@pytest.mark.asyncio
async def test_resume_controller_failure():
    """Test resume_controller failure"""
    from app.controllers.resume_controller import upload_resumes_controller
    
    mock_db = AsyncMock()
    mock_files = [UploadFile(file=BytesIO(b""), filename="invalid.txt")]
    
    with patch('app.controllers.resume_controller.ResumeService') as MockService:
        mock_instance = MockService.return_value
        mock_instance.process_resume_upload.return_value = {
            'status': 'validation_failure',
            'saved_count': 0,
            'skipped_files': ['invalid.txt'],
            'message': 'Invalid format'
        }
        
        result = await upload_resumes_controller("job1", mock_files, mock_db)
        assert result['status_code'] == 400


# =================================================================================================
# public_search_service.py (88%, 87 lines) - Service
# =================================================================================================

@pytest.mark.asyncio
async def test_public_search_service_suggestions():
    """Test public_search_service suggestions"""
    from app.services.job_post.public_search_service import PublicSearchService
    
    mock_db = AsyncMock()
    service = PublicSearchService(mock_db)
    
    with patch('app.services.job_post.public_search_service.get_search_autocomplete_suggestions', return_value={"skills": []}):
        result = await service.get_suggestions()
        assert "skills" in result


@pytest.mark.asyncio
async def test_public_search_service_search():
    """Test public_search_service search"""
    from app.services.job_post.public_search_service import PublicSearchService
    
    mock_db = AsyncMock()
    service = PublicSearchService(mock_db)
    
    mock_job = MagicMock()
    mock_job.descriptions = []
    
    with patch('app.services.job_post.public_search_service.search_active_job_details', return_value=[(mock_job, 0.9)]):
        with patch('app.services.job_post.public_search_service.JobPostSerializer.format_job_details_orm', return_value={}):
            result = await service.search_jobs("role", [], [])
            assert len(result) == 1
            assert result[0]['score'] == 0.9


# =================================================================================================
# job_post_permissions.py (94%, 75 lines) - Service/Utils
# =================================================================================================

def test_job_post_permissions_can_edit():
    """Test job_post_permissions can_edit_job"""
    from app.services.job_post.job_post_permissions import JobPostPermissions
    from types import SimpleNamespace
    
    job = SimpleNamespace(user_id="u1")
    
    # Owner
    assert JobPostPermissions.can_edit_job(job, {"user_id": "u1", "role": "USER"}) is True
    
    # Admin
    assert JobPostPermissions.can_edit_job(job, {"user_id": "u2", "role": "SUPER_ADMIN"}) is True
    
    # Other user
    assert JobPostPermissions.can_edit_job(job, {"user_id": "u2", "role": "USER"}) is False


def test_job_post_permissions_filter():
    """Test job_post_permissions filter_jobs_by_ownership"""
    from app.services.job_post.job_post_permissions import JobPostPermissions
    
    jobs = [{"user_id": "u1"}, {"user_id": "u2"}]
    
    # Filter own only
    filtered = JobPostPermissions.filter_jobs_by_ownership(jobs, {"user_id": "u1", "role": "USER"}, show_own_only=True)
    assert len(filtered) == 1
    assert filtered[0]['user_id'] == "u1"


# =================================================================================================
# update_jd_request.py (100%, 97 lines) - Schema
# =================================================================================================

def test_update_jd_request_validation():
    """Test update_jd_request validation"""
    from app.schemas.update_jd_request import UpdateJdRequest
    from datetime import datetime
    
    # Valid
    req = UpdateJdRequest(
        job_title="Title",
        minimum_experience=1,
        maximum_experience=5,
        active_till=datetime.now(),
        skills_required=[{"skill": "Python", "weightage": 5}],
        description_sections=[{"title": "T", "content": "C"}],
        job_description="Desc",
        job_location="Loc"
    )
    assert req.maximum_experience >= req.minimum_experience

    # Invalid experience
    with pytest.raises(ValueError):
        UpdateJdRequest(
            job_title="Title",
            minimum_experience=5,
            maximum_experience=1,
            active_till=datetime.now(),
            skills_required=[],
            description_sections=[]
        )


# =================================================================================================
# analyze_jd/base.py (100%, 21 lines) - Abstract Base Class
# =================================================================================================

def test_analyze_jd_base():
    """Test AnalyzeJDBase instantiation"""
    from app.services.job_post.analyze_jd.base import BaseAnalyzeJD
    
    # Cannot instantiate abstract class
    with pytest.raises(TypeError):
        BaseAnalyzeJD()


# =================================================================================================
# upload_jd/base.py (100%, 10 lines) - Abstract Base Class
# =================================================================================================

def test_upload_jd_base():
    """Test UploadJDBase instantiation"""
    from app.services.job_post.upload_jd.base import BaseUploadJobPost
    
    # Cannot instantiate abstract class
    with pytest.raises(TypeError):
        BaseUploadJobPost()


# =================================================================================================
# career_application_service.py (75%, 176 lines) - Service
# =================================================================================================

@pytest.mark.asyncio
async def test_career_application_send_otp():
    """Test career_application_service send_otp"""
    from app.services.job_post.career_application_service import CareerApplicationService
    
    mock_cache = AsyncMock()
    service = CareerApplicationService(mock_cache)
    
    with patch('app.services.job_post.career_application_service.AsyncSessionLocal') as mock_db_ctx:
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__.return_value = mock_db
        
        # Mock no existing application
        mock_db.execute.return_value.scalars.return_value.first.return_value = None
        
        with patch('app.services.job_post.career_application_service.send_otp_email', return_value=True):
            result = await service.send_otp("job1", "test@test.com")
            assert result['status_code'] == 200


@pytest.mark.asyncio
async def test_career_application_verify_otp():
    """Test career_application_service verify_otp"""
    from app.services.job_post.career_application_service import CareerApplicationService
    import json
    
    mock_cache = AsyncMock()
    service = CareerApplicationService(mock_cache)
    
    # Mock stored OTP
    mock_cache.hget.return_value = json.dumps({"otp": "123456"})
    
    result = await service.verify_otp_and_submit_application("job1", "test@test.com", "123456", {})
    assert result['status_code'] == 200


# =================================================================================================
# agent_config_service.py (80%, 147 lines) - Service
# =================================================================================================

@pytest.mark.asyncio
async def test_agent_config_service_update():
    """Test agent_config_service update_job_agent_config"""
    from app.services.config_service.agent_config_service import AgentConfigService
    from app.schemas.config_request import AgentRoundConfigUpdate
    from uuid import uuid4
    
    mock_db = AsyncMock()
    service = AgentConfigService(mock_db)
    
    job_id = str(uuid4())
    user_id = str(uuid4())
    
    # Mock job ownership
    mock_job = MagicMock()
    mock_job.user_id = uuid4() # Mismatch
    mock_db.get.return_value = mock_job
    
    # Should raise Forbidden if user mismatch
    # But we need to match UUIDs. Let's make them match for success or mismatch for failure.
    # Test failure first
    
    with pytest.raises(HTTPException) as exc_info:
        await service.update_job_agent_config(job_id, user_id, [])
    
    assert exc_info.value.status_code == 403
