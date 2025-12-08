import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.controllers.resume_controller import upload_resumes_controller, handle_resume_upload
from fastapi import status

@pytest.mark.asyncio
async def test_resume_controller_partial_success(fake_db):
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files, **k):
            return {
                'status': 'success',
                'saved_count': 1,
                'skipped_files': ['bad.exe'],
                'task_id': 't1'
            }
            
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", [], fake_db)
        assert res['status_code'] == 202
        assert "1 resume(s) uploaded" in res['message']
        assert "bad.exe" in res['message']


@pytest.mark.asyncio
async def test_handle_resume_upload_exception_with_files(fake_db):
    """Test handle_resume_upload exception path with files list - covers lines 39-46"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files, **k):
            raise RuntimeError("Service failed")
    
    # Create file dictionaries since the code accesses f["filename"]
    files = [
        {"filename": "file1.pdf"},
        {"filename": "file2.pdf"}
    ]
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await handle_resume_upload("j1", files, form_metadata=None, db=fake_db)
        assert res['status'] == 'failure'
        assert res['saved_count'] == 0
        assert 'file1.pdf' in res['skipped_files']
        assert 'file2.pdf' in res['skipped_files']
        assert 'Service failed' in res['message']


@pytest.mark.asyncio
async def test_handle_resume_upload_with_form_metadata(fake_db):
    """Test form_metadata attachment when result is dict - covers lines 35-36"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files, **k):
            return {'status': 'success', 'saved_count': 1}
    
    form_data = {'name': 'John', 'email': 'john@test.com'}
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await handle_resume_upload("j1", [], form_metadata=form_data, db=fake_db)
        assert res['form_metadata'] == form_data
        assert res['status'] == 'success'


@pytest.mark.asyncio
async def test_upload_resumes_all_files_skipped(fake_db):
    """Test all files skipped validation - covers lines 69-70, 81"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files):
            return {
                'status': 'validation_failure',
                'saved_count': 0,
                'skipped_files': ['bad1.exe', 'bad2.txt'],
                'message': 'Invalid format'
            }
    
    mock_file1 = MagicMock()
    mock_file1.filename = "bad1.exe"
    mock_file2 = MagicMock()
    mock_file2.filename = "bad2.txt"
    files = [mock_file1, mock_file2]
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", files, fake_db)
        assert res['status_code'] == status.HTTP_400_BAD_REQUEST
        assert '2 file(s) were provided' in res['message']
        assert 'all were skipped' in res['message']
        assert 'bad1.exe' in res['message']
        assert 'bad2.txt' in res['message']


@pytest.mark.asyncio
async def test_upload_resumes_success_no_skipped_files(fake_db):
    """Test success with no skipped files - covers line 85"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files):
            return {
                'status': 'success',
                'saved_count': 2,
                'skipped_files': [],
                'message': 'All uploaded'
            }
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", [], fake_db)
        assert res['status_code'] == status.HTTP_202_ACCEPTED
        assert '2 resume(s) uploaded' in res['message']
        assert 'skipped' not in res['message']


@pytest.mark.asyncio
async def test_upload_resumes_with_saved_files(fake_db):
    """Test including saved_files in response - covers line 100"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files):
            return {
                'status': 'success',
                'saved_count': 2,
                'skipped_files': [],
                'task_id': 'task123',
                'saved_files': ['resume1.pdf', 'resume2.pdf']
            }
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", [], fake_db)
        assert res['status_code'] == status.HTTP_202_ACCEPTED
        assert res['data']['saved_files'] == ['resume1.pdf', 'resume2.pdf']
        assert res['data']['task_id'] == 'task123'


@pytest.mark.asyncio
async def test_upload_resumes_validation_failure_explicit(fake_db):
    """Test explicit validation_failure status - covers lines 107-113"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files):
            return {
                'status': 'validation_failure',
                'saved_count': 0,
                'skipped_files': ['invalid.pdf'],
                'message': 'Validation failed'
            }
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", [MagicMock()], fake_db)
        assert res['status_code'] == status.HTTP_400_BAD_REQUEST
        assert 'errors' in res


@pytest.mark.asyncio
async def test_upload_resumes_full_failure_no_skipped(fake_db):
    """Test complete failure with no skipped files - covers line 85"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files):
            return {
                'status': 'error',
                'saved_count': 0,
                'skipped_files': [],
                'message': 'Job not found'
            }
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", [], fake_db)
        # When saved_count=0 and no skipped files, returns 400
        assert res['status_code'] == 400
        assert 'Job not found' in res['message']


@pytest.mark.asyncio
async def test_upload_resumes_top_level_exception(fake_db):
    """Test top-level exception handler - covers lines 120-124"""
    class FakeService:
        def __init__(self, db): pass
        async def process_resume_upload(self, jid, files):
            raise ValueError("Unexpected error during processing")
    
    with patch('app.controllers.resume_controller.ResumeService', FakeService):
        res = await upload_resumes_controller("j1", [], fake_db)
        assert res['status_code'] == 500
        assert 'Unexpected internal server error' in res['message']
        assert 'Unexpected error during processing' in res['message']