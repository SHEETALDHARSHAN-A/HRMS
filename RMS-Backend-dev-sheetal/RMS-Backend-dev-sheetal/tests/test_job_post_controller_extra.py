import pytest
from unittest.mock import MagicMock

from fastapi.responses import JSONResponse

from app.controllers import job_post_controller as jp_ctrl
from app.utils.standard_response_utils import ResponseBuilder


@pytest.mark.asyncio
async def test_upload_job_post_controller_success(monkeypatch):
    class FakeUploader:
        def __init__(self, redis_store=None):
            pass

        async def job_details_file_upload(self, file):
            return {"job_details": {"job_id": "123", "title": "Dev"}}

    monkeypatch.setattr(jp_ctrl, "UploadJobPost", FakeUploader)

    # file can be any object; controller passes it through to service
    fake_file = MagicMock()
    res = await jp_ctrl.upload_job_post_controller(file=fake_file, jd_uploader=FakeUploader())
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert res.get("data").get("extracted_details").get("job_id") == "123"


@pytest.mark.asyncio
async def test_get_public_job_by_id_controller_active_and_inactive(monkeypatch):
    # Fake get_db async generator
    async def fake_get_db():
        yield MagicMock()

    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"job_id": job_id, "is_active": True, "job_title": "T", "job_location": "Loc", "work_from_home": False, "skills_required": [], "minimum_experience": 1, "maximum_experience": 3, "salary": 100}

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)

    # active job
    res = await jp_ctrl.get_public_job_by_id_controller("111")
    assert res.get("success") is True
    assert res.get("data").get("job").get("job_id") == "111"

    # inactive job
    class FakeReaderInactive(FakeReader):
        def get_job(self, job_id):
            d = super().get_job(job_id)
            d["is_active"] = False
            return d

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReaderInactive)
    res2 = await jp_ctrl.get_public_job_by_id_controller("222")
    assert res2.get("success") is False
    assert res2.get("status_code") == 404


@pytest.mark.asyncio
async def test_toggle_job_status_permission_and_success(monkeypatch):
    async def fake_get_db():
        yield MagicMock()

    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    # Reader returns a job with created_by_user_id
    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"job_id": job_id, "created_by_user_id": "owner-1", "is_active": False}

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)

    # permission denied
    monkeypatch.setattr(jp_ctrl.JobPostPermissions, "can_edit_job", staticmethod(lambda job, user: False))
    res = await jp_ctrl.toggle_job_status_controller("j1", True, request=MagicMock())
    assert res.get("success") is False
    assert res.get("status_code") == 403

    # permission allowed and service returns dict
    monkeypatch.setattr(jp_ctrl.JobPostPermissions, "can_edit_job", staticmethod(lambda job, user: True))

    class FakeUpdate:
        def __init__(self, db):
            pass

        def toggle_status(self, job_id, is_active):
            return {"success": True, "data": {"job_id": job_id, "is_active": is_active}}

    monkeypatch.setattr(jp_ctrl, "UpdateJobPost", FakeUpdate)

    res2 = await jp_ctrl.toggle_job_status_controller("j1", True, request=MagicMock())
    assert res2.get("success") is True


@pytest.mark.asyncio
async def test_delete_job_post_controller_permission_and_success(monkeypatch):
    async def fake_get_db():
        yield MagicMock()

    monkeypatch.setattr(jp_ctrl, "get_db", fake_get_db)

    class FakeReader:
        def __init__(self, db):
            pass

        def get_job(self, job_id):
            return {"job_id": job_id, "created_by_user_id": "owner-1"}

    monkeypatch.setattr(jp_ctrl, "JobPostReader", FakeReader)

    # permission denied
    monkeypatch.setattr(jp_ctrl.JobPostPermissions, "can_edit_job", staticmethod(lambda job, user: False))
    res = await jp_ctrl.delete_job_post_controller("j1", request=MagicMock())
    assert res.get("success") is False
    assert res.get("status_code") == 403

    # permission allowed and service returns dict
    monkeypatch.setattr(jp_ctrl.JobPostPermissions, "can_edit_job", staticmethod(lambda job, user: True))

    class FakeUpdate:
        def __init__(self, db):
            pass

        def delete_job_post(self, job_id):
            return {"success": True, "message": "deleted", "data": {"job_id": job_id}}

    monkeypatch.setattr(jp_ctrl, "UpdateJobPost", FakeUpdate)

    res2 = await jp_ctrl.delete_job_post_controller("j1", request=MagicMock())
    assert res2.get("success") is True
import pytest
from unittest.mock import patch
from types import SimpleNamespace
from fastapi import status

from app.controllers.job_post_controller import get_job_by_id_controller, delete_job_post_controller


@pytest.mark.asyncio
async def test_get_job_by_id_controller_invalid_uuid():
    res = await get_job_by_id_controller("not-a-uuid", request=None)
    assert isinstance(res, dict)
    assert res.get("status_code") == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@patch("app.controllers.job_post_controller.JobPostReader")
@patch("app.controllers.job_post_controller.UpdateJobPost")
async def test_delete_job_post_controller_success(MockUpdateJobPost, MockJobPostReader):
    mock_reader = MockJobPostReader.return_value
    mock_reader.get_job.return_value = {"user_id": "auth-user-id", "job_id": "abc"}

    mock_service = MockUpdateJobPost.return_value
    mock_service.delete_job_post.return_value = {"success": True, "status_code": status.HTTP_200_OK}

    # call controller with a fake request object that has state.user
    fake_request = SimpleNamespace()
    fake_request.state = SimpleNamespace(user={"user_id": "auth-user-id", "sub": "auth-user-id"})

    res = await delete_job_post_controller("abc", request=fake_request)
    assert isinstance(res, dict)
    assert res.get("success") is True