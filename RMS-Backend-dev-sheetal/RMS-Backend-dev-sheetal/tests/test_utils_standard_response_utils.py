import pytest
from fastapi import status
from app.utils.standard_response_utils import ResponseBuilder, StandardResponse


def test_response_builder_success_and_created():
    res = ResponseBuilder.success("ok", data={"x": 1})
    assert res["success"] is True
    assert res["status_code"] == status.HTTP_200_OK
    assert res["message"] == "ok"

    created = ResponseBuilder.created("created", data=None)
    assert created["status_code"] == status.HTTP_201_CREATED


def test_response_builder_error_and_helpers():
    err = ResponseBuilder.error("bad")
    assert err["success"] is False
    assert err["status_code"] == status.HTTP_400_BAD_REQUEST
    assert err["errors"] == ["bad"]

    nf = ResponseBuilder.not_found()
    assert nf["status_code"] == status.HTTP_404_NOT_FOUND

    cf = ResponseBuilder.conflict()
    assert cf["status_code"] == status.HTTP_409_CONFLICT

    se = ResponseBuilder.server_error()
    assert se["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_standard_response_object_to_dict():
    obj = StandardResponse(success=True, status_code=status.HTTP_200_OK, message="m", data={"a":1})
    d = obj.to_dict()
    assert d["success"] is True
    assert d["data"]["a"] == 1

    obj2 = StandardResponse(success=False, status_code=status.HTTP_400_BAD_REQUEST, message="err", errors=["e1"]) 
    d2 = obj2.to_dict()
    assert d2["success"] is False
    assert d2["errors"] == ["e1"]
