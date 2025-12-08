import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services.job_post.analyze_jd.analyze_job_post import AnalyzeJobPost


@pytest.mark.asyncio
async def test__get_recommended_skills_agent_error_raises_http():
    svc = AnalyzeJobPost()
    svc._create_agent = lambda: {"error": "no key"}
    with pytest.raises(HTTPException):
        await svc._get_recommended_skills("Title", "Some description that is long enough to pass initial checks")

@pytest.mark.asyncio
async def test__get_recommended_skills_parses_json_from_final_output():
    svc = AnalyzeJobPost()

    # Provide a dummy agent object
    svc._create_agent = lambda: object()
    final_output = '```json\n{"recommended_skills": [{"skill": "Python", "weight": 10}]}\n```'
    runner_result = SimpleNamespace(final_output=final_output)

    with patch('app.services.job_post.analyze_jd.analyze_job_post.Runner') as MockRunner:
        MockRunner.run = AsyncMock(return_value=runner_result)
        res = await svc._get_recommended_skills("Dev", "This is a long enough job description to be fine.")

    assert isinstance(res, list)
    assert res[0]["skill"] == "Python"


@pytest.mark.asyncio
async def test_analyze_job_details_validation_short_description_raises():
    svc = AnalyzeJobPost()
    jd = SimpleNamespace(job_title="Dev", job_description="too short")

    with pytest.raises(HTTPException):
        await svc.analyze_job_details(jd)


@pytest.mark.asyncio
async def test_analyze_job_details_happy_path_returns_expected():
    svc = AnalyzeJobPost()
    long_desc = "A" * 250
    jd = SimpleNamespace(job_title="Developer", job_description=long_desc)

    # Patch _get_recommended_skills to avoid calling LLM
    svc._get_recommended_skills = AsyncMock(return_value=[{"skill": "Python"}])

    res = await svc.analyze_job_details(jd)

    assert res["job_title"] == "Developer"
    assert isinstance(res["recommended_skills"], list)
    assert res["recommended_skills"][0]["skill"] == "Python"
