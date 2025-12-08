import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException, status
from datetime import datetime

from app.services.shortlist_service.shortlist_service import ShortlistService
import app.services.shortlist_service.shortlist_service as service_mod
from app.schemas.update_shortlist_request import UpdateShortlistRequest


@pytest.mark.asyncio
async def test_get_job_round_overview_success(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(service_mod, 'get_job_round_overview', AsyncMock(return_value=[{'job_id': '1'}]))
    srv = ShortlistService(db)
    res = await srv.get_job_round_overview()
    assert isinstance(res, list)


@pytest.mark.asyncio
async def test_get_job_round_overview_error(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(service_mod, 'get_job_round_overview', AsyncMock(side_effect=Exception('boom')))
    srv = ShortlistService(db)
    with pytest.raises(HTTPException) as excinfo:
        await srv.get_job_round_overview()
    assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_candidates_by_job_and_round_success(monkeypatch):
    db = SimpleNamespace()
    sample = [{'profile_id': 'p1'}]
    monkeypatch.setattr(service_mod, 'get_round_candidates', AsyncMock(return_value=sample))
    srv = ShortlistService(db)
    res = await srv.get_candidates_by_job_and_round('job', 'round')
    assert res == sample


@pytest.mark.asyncio
async def test_get_candidates_by_job_and_round_error(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(service_mod, 'get_round_candidates', AsyncMock(side_effect=Exception('nope')))
    srv = ShortlistService(db)
    with pytest.raises(HTTPException) as excinfo:
        await srv.get_candidates_by_job_and_round('job', 'round')
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_candidate_status_success(monkeypatch):
    db = SimpleNamespace()
    srv = ShortlistService(db)
    updated_entry = SimpleNamespace(id=1, profile_id='p1', job_id='job', result='shortlist', reason='test', updated_at=datetime.utcnow())
    monkeypatch.setattr(service_mod, 'upsert_shortlist_result', AsyncMock(return_value=updated_entry))
    monkeypatch.setattr(service_mod, 'update_interview_round_status', AsyncMock(return_value=True))
    payload = UpdateShortlistRequest(new_result='shortlist', reason='ok')
    res = await srv.update_candidate_status('p1', 'r1', payload)
    assert res['new_result'] == 'shortlist'
    assert res['new_round_status'] == 'shortlisted'


@pytest.mark.asyncio
async def test_update_candidate_status_invalid_result(monkeypatch):
    db = SimpleNamespace()
    srv = ShortlistService(db)
    payload = UpdateShortlistRequest(new_result='notvalid', reason='ok')
    with pytest.raises(HTTPException) as excinfo:
        await srv.update_candidate_status('p1', 'r1', payload)
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_candidate_status_round_update_failed(monkeypatch):
    db = SimpleNamespace()
    srv = ShortlistService(db)
    updated_entry = SimpleNamespace(id=1, profile_id='p1', job_id='job', result='shortlist', reason='test', updated_at=datetime.utcnow())
    monkeypatch.setattr(service_mod, 'upsert_shortlist_result', AsyncMock(return_value=updated_entry))
    monkeypatch.setattr(service_mod, 'update_interview_round_status', AsyncMock(return_value=False))
    payload = UpdateShortlistRequest(new_result='shortlist', reason='ok')
    with pytest.raises(HTTPException) as excinfo:
        await srv.update_candidate_status('p1', 'r1', payload)
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_candidate_status_upsert_raises(monkeypatch):
    db = SimpleNamespace()
    srv = ShortlistService(db)
    monkeypatch.setattr(service_mod, 'upsert_shortlist_result', AsyncMock(side_effect=ValueError('fail')))
    payload = UpdateShortlistRequest(new_result='shortlist', reason='ok')
    with pytest.raises(HTTPException) as excinfo:
        await srv.update_candidate_status('p1', 'r1', payload)
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
