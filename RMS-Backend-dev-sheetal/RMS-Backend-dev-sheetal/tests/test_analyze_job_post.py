import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.services.job_post.analyze_jd.analyze_job_post import AnalyzeJobPost
from app.schemas.analyze_jd_request import AnalyzeJdRequest


@pytest.mark.asyncio
async def test_analyze_job_details_title_too_short():
    svc = AnalyzeJobPost()
    req = AnalyzeJdRequest(job_title='a', job_description='x'*300)
    with pytest.raises(HTTPException):
        await svc.analyze_job_details(req)


@pytest.mark.asyncio
async def test_analyze_job_details_description_too_short():
    svc = AnalyzeJobPost()
    req = AnalyzeJdRequest(job_title='Valid Title', job_description='short')
    with pytest.raises(HTTPException):
        await svc.analyze_job_details(req)


@pytest.mark.asyncio
async def test_analyze_job_details_invalid_placeholders():
    svc = AnalyzeJobPost()
    req = AnalyzeJdRequest(job_title='string', job_description='string'*50)
    with pytest.raises(HTTPException):
        await svc.analyze_job_details(req)


@pytest.mark.asyncio
async def test_get_recommended_skills_success(monkeypatch):
    svc = AnalyzeJobPost()
    # Patch _create_agent to return non-dict
    monkeypatch.setattr(svc, '_create_agent', lambda: SimpleNamespace())
    # Patch Runner.run to return an object with final_output JSON
    res_obj = SimpleNamespace(final_output='{"recommended_skills": [{"skill": "Python"}]}')
    monkeypatch.setattr('app.services.job_post.analyze_jd.analyze_job_post.Runner', SimpleNamespace(run=AsyncMock(return_value=res_obj)))
    skills = await svc._get_recommended_skills('T', 'D'*300)
    assert isinstance(skills, list)


@pytest.mark.asyncio
async def test_get_recommended_skills_empty_output(monkeypatch):
    svc = AnalyzeJobPost()
    monkeypatch.setattr(svc, '_create_agent', lambda: SimpleNamespace())
    res_obj = SimpleNamespace(final_output='')
    monkeypatch.setattr('app.services.job_post.analyze_jd.analyze_job_post.Runner', SimpleNamespace(run=AsyncMock(return_value=res_obj)))
    with pytest.raises(HTTPException):
        await svc._get_recommended_skills('T', 'D'*300)
