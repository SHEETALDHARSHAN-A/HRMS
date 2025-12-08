import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException, status
import uuid

from app.controllers import shortlist_controller as ctrl
from app.schemas.update_shortlist_request import UpdateShortlistRequest
from app.services.shortlist_service.shortlist_service import ShortlistService


@pytest.mark.asyncio
async def test_validate_uuid_bad_uuid_raises():
    with pytest.raises(HTTPException):
        ctrl._validate_uuid('not-a-uuid', 'job_id')


@pytest.mark.asyncio
async def test_get_job_round_overview_success(monkeypatch, fake_db):
    sample_overview = [{'job_id': str(uuid.uuid4()), 'rounds': []}]
    monkeypatch.setattr(ShortlistService, 'get_job_round_overview', AsyncMock(return_value=sample_overview))
    resp = await ctrl.get_job_round_overview_controller(fake_db)
    assert resp['success'] is True
    assert 'job_round_overview' in resp['data']


@pytest.mark.asyncio
async def test_get_job_round_overview_error(monkeypatch, fake_db):
    monkeypatch.setattr(ShortlistService, 'get_job_round_overview', AsyncMock(side_effect=Exception('boom')))
    resp = await ctrl.get_job_round_overview_controller(fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_all_candidates_success(monkeypatch, fake_db):
    job_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    results = [{'profile_id': '1'}]
    monkeypatch.setattr(ShortlistService, 'get_candidates_by_job_and_round', AsyncMock(return_value=results))
    resp = await ctrl.get_all_candidates_controller(job_id, round_id, None, fake_db)
    assert resp['success'] is True
    assert resp['data']['candidates'] == results


@pytest.mark.asyncio
async def test_get_all_candidates_not_found(monkeypatch, fake_db):
    job_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    monkeypatch.setattr(ShortlistService, 'get_candidates_by_job_and_round', AsyncMock(return_value=[]))
    resp = await ctrl.get_all_candidates_controller(job_id, round_id, None, fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_all_candidates_invalid_uuid(monkeypatch, fake_db):
    resp = await ctrl.get_all_candidates_controller('bad', 'also-bad', None, fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_candidate_status_success(monkeypatch, fake_db):
    profile_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    payload = UpdateShortlistRequest(new_result='pass')
    updated = {'profile_id': profile_id, 'result': 'pass'}
    monkeypatch.setattr(ShortlistService, 'update_candidate_status', AsyncMock(return_value=updated))
    resp = await ctrl.update_candidate_status_controller(profile_id, round_id, payload, fake_db)
    assert resp['success'] is True
    assert resp['data']['updated_candidate'] == updated


@pytest.mark.asyncio
async def test_update_candidate_status_failure(monkeypatch, fake_db):
    profile_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    payload = UpdateShortlistRequest(new_result='pass')
    monkeypatch.setattr(ShortlistService, 'update_candidate_status', AsyncMock(return_value=None))
    resp = await ctrl.update_candidate_status_controller(profile_id, round_id, payload, fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_update_candidate_status_invalid_uuid(monkeypatch, fake_db):
    payload = UpdateShortlistRequest(new_result='pass')
    resp = await ctrl.update_candidate_status_controller('bad', 'also-bad', payload, fake_db)
    assert resp['success'] is False
    assert resp['status_code'] == status.HTTP_400_BAD_REQUEST
