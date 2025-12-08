import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.job_post.public_search_service import PublicSearchService
import app.services.job_post.public_search_service as service_mod


@pytest.mark.asyncio
async def test_get_suggestions_success(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(service_mod, 'get_search_autocomplete_suggestions', AsyncMock(return_value={'skills': ['Python']}))
    srv = PublicSearchService(db)
    res = await srv.get_suggestions()
    assert res['skills'] == ['Python']


@pytest.mark.asyncio
async def test_get_suggestions_error(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(service_mod, 'get_search_autocomplete_suggestions', AsyncMock(side_effect=Exception('boom')))
    srv = PublicSearchService(db)
    with pytest.raises(Exception):
        await srv.get_suggestions()


@pytest.mark.asyncio
async def test_search_jobs_empty(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(service_mod, 'search_active_job_details', AsyncMock(return_value=[]))
    srv = PublicSearchService(db)
    res = await srv.search_jobs('role', [], [])
    assert res == []


@pytest.mark.asyncio
async def test_search_jobs_with_results(monkeypatch):
    db = SimpleNamespace()
    # Create fake job ORM with descriptions
    desc = SimpleNamespace(type_description='Job Overview', context='Detailed description')
    job_orm = SimpleNamespace(descriptions=[desc])
    monkeypatch.setattr(service_mod, 'search_active_job_details', AsyncMock(return_value=[(job_orm, 0.75)]))
    monkeypatch.setattr(service_mod.JobPostSerializer, 'format_job_details_orm', lambda j: {'id': 'job1'})
    srv = PublicSearchService(db)
    res = await srv.search_jobs('role', [], [])
    assert len(res) == 1
    assert res[0]['score'] == 0.75
    assert 'short_description' in res[0]
