from app.utils.standard_response_utils import ResponseBuilder, StandardResponse
from fastapi import status


def test_response_builder_success_created_and_error_shapes():
    # success
    r = ResponseBuilder.success("ok", data={"x": 1}, status_code=status.HTTP_200_OK)
    assert r["success"] is True
    assert r["message"] == "ok"
    assert r["data"] == {"x": 1}
    assert r["status_code"] == status.HTTP_200_OK

    # created
    c = ResponseBuilder.created("created", data={"id": 1})
    assert c["success"] is True
    assert c["status_code"] == status.HTTP_201_CREATED

    # error with explicit errors
    e = ResponseBuilder.error("bad", errors=["e1"], status_code=status.HTTP_400_BAD_REQUEST)
    assert e["success"] is False
    assert e["errors"] == ["e1"]
    assert e["status_code"] == status.HTTP_400_BAD_REQUEST

    # not_found / conflict / server_error convenience
    nf = ResponseBuilder.not_found("no")
    assert nf["success"] is False and nf["status_code"] == status.HTTP_404_NOT_FOUND

    cf = ResponseBuilder.conflict()
    assert cf["success"] is False and cf["status_code"] == status.HTTP_409_CONFLICT

    se = ResponseBuilder.server_error()
    assert se["success"] is False and se["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_standard_response_to_dict_and_errors_default():
    # When success=True and no errors passed, errors should be None
    sr = StandardResponse(success=True, status_code=200, message="ok", data={"a": 1})
    d = sr.to_dict()
    assert d["success"] is True
    assert d["errors"] is None

    # When success=False and no errors passed, errors becomes an empty list
    sr2 = StandardResponse(success=False, status_code=400, message="bad")
    d2 = sr2.to_dict()
    assert d2["success"] is False
    assert isinstance(d2["errors"], list)
from app.utils.standard_response_utils import ResponseBuilder


def test_response_builder_success_and_error():
    s = ResponseBuilder.success("ok", data={"a":1}, status_code=200)
    assert s["success"] is True
    assert s["data"]["a"] == 1

    e = ResponseBuilder.error("bad", errors=["x"], status_code=400)
    assert e["success"] is False
    assert e["errors"] == ["x"]

    nf = ResponseBuilder.not_found()
    assert nf["status_code"] == 404

    se = ResponseBuilder.server_error()
    assert se["status_code"] == 500
