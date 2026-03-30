import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_get_coding_question_route_success(monkeypatch):
    from app.api.v1.coding_routes import get_coding_question_route

    class FakeService:
        def __init__(self, db):
            pass

        async def get_question(self, token: str, email: str):
            assert token == "token-1"
            assert email == "candidate@example.com"
            return {"title": "Two Sum", "problem": "Solve it", "languages": ["python"]}

    monkeypatch.setattr("app.api.v1.coding_routes.CodingService", FakeService)

    res = await get_coding_question_route(token="token-1", email="candidate@example.com", db=object())
    assert res["success"] is True
    assert res["data"]["title"] == "Two Sum"


@pytest.mark.asyncio
async def test_submit_coding_solution_route_http_error(monkeypatch):
    from app.api.v1.coding_routes import submit_coding_solution_route
    from app.schemas.coding_request import CodingSubmitRequest

    class FakeService:
        def __init__(self, db):
            pass

        async def submit_solution(self, request):
            raise HTTPException(status_code=400, detail="Coding challenge is not enabled")

    monkeypatch.setattr("app.api.v1.coding_routes.CodingService", FakeService)

    request = CodingSubmitRequest(
        token="token-1",
        email="candidate@example.com",
        language="python",
        code="print('x')",
        question={"title": "Sample"},
    )
    res = await submit_coding_solution_route(request=request, db=object())
    assert res["success"] is False
    assert res["status_code"] == 400


@pytest.mark.asyncio
async def test_get_coding_submission_route_not_found(monkeypatch):
    from app.api.v1.coding_routes import get_coding_submission_route

    class FakeService:
        def __init__(self, db):
            pass

        async def get_submission(self, submission_id: str, token: str, email: str):
            raise HTTPException(status_code=404, detail="Submission not found")

    monkeypatch.setattr("app.api.v1.coding_routes.CodingService", FakeService)

    res = await get_coding_submission_route(
        submission_id="d09f2b53-efad-4f55-b679-9f22f4fa1d5c",
        token="token-1",
        email="candidate@example.com",
        db=object(),
    )
    assert res["success"] is False
    assert res["status_code"] == 404
