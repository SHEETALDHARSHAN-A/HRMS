import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request
from app.controllers import job_post_controller as controller
from app.utils.standard_response_utils import ResponseBuilder


def test_to_dict_handles_none_and_dict_and_model_versions():
    assert controller._to_dict(None) is None
    assert controller._to_dict({"a":1}) == {"a":1}

    class Pyd2:
        def model_dump(self):
            return {"a":2}
    assert controller._to_dict(Pyd2()) == {"a":2}

    class Pyd1:
        def dict(self):
            return {"b":3}
    assert controller._to_dict(Pyd1()) == {"b":3}


def test_get_current_user_from_request_state():
    req = MagicMock()
    req.state.user = {"sub":"u123"}
    out = controller._get_current_user(req)
    assert isinstance(out, dict)
    assert out["user_id"] == "u123"


def test_handle_controller_exception_returns_500():
    resp = controller._handle_controller_exception(Exception("boom"), job_id="id", operation="upd")
    assert resp.status_code == 500
    assert "An unexpected error occurred during the upd" in resp.body.decode()


@pytest.mark.asyncio
async def test_upload_job_post_controller_success_and_error(monkeypatch):
    file = MagicMock()
    # Success path
    uploader = AsyncMock()
    success_result = {"job_details":{"job_id": "x"}}
    uploader.job_details_file_upload = AsyncMock(return_value=success_result)
    res = await controller.upload_job_post_controller(file=file, jd_uploader=uploader)
    assert res["success"] is True

    # Error path - service returns error in dict
    uploader.job_details_file_upload = AsyncMock(return_value={"error":"bad"})
    res = await controller.upload_job_post_controller(file=file, jd_uploader=uploader)
    assert res["success"] is False

    # Exception path
    uploader.job_details_file_upload = AsyncMock(side_effect=Exception("boom"))
    res = await controller.upload_job_post_controller(file=file, jd_uploader=uploader)
    assert hasattr(res, "status_code")
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_update_job_post_controller_unauthorized():
    # If request.state.user is missing, it should return 401
    job_details = MagicMock()
    req = MagicMock()
    req.state = MagicMock()
    req.state.user = None
    res = await controller.update_job_post_controller(job_details=job_details, request=req)
    assert res["success"] is False
    assert res["status_code"] == 401
