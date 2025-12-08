import pytest
from types import SimpleNamespace
from app.services.notification.invitation_service import InvitationService
from app.db.repository import notification_repository as repo
from app.services.notification import invitation_service as svcmod
from app.utils.standard_response_utils import ResponseBuilder


@pytest.mark.asyncio
async def test_get_invitations_by_inviter_happy_path(monkeypatch):
    # Prepare an invitation with accepted_user_id
    invitation = SimpleNamespace(
        invitation_id='i1',
        invited_email='a@b.com',
        invited_first_name='A',
        invited_last_name='B',
        invited_role='ADMIN',
        status='PENDING',
        created_at=None,
        expires_at=None,
        accepted_at=None,
        accepted_user_id='u1'
    )

    # Monkeypatch fetch_invitations_by_inviter to return our list
    async def fake_fetch_invitations(db, user_id, status_filter=None):
        return [invitation]

    async def fake_fetch_user_by_id(db, user_id):
        return SimpleNamespace(user_id='u1', first_name='John', last_name='Doe', email='john@example.com')

    # The service imports these functions at module-level; patch them at service module
    monkeypatch.setattr(svcmod, 'fetch_invitations_by_inviter', fake_fetch_invitations)
    monkeypatch.setattr(svcmod, 'fetch_user_by_id', fake_fetch_user_by_id)

    svc = InvitationService(db=None)
    res = await svc.get_invitations_by_inviter('u1')
    assert res['status_code'] == 200
    assert 'invitations' in res['data']
    inv = res['data']['invitations'][0]
    assert inv['accepted_user']['user_id'] == 'u1'


@pytest.mark.asyncio
async def test_get_invitations_by_inviter_error_path(monkeypatch):
    async def raising_fetch(db, user_id, status_filter=None):
        raise Exception('boom')

    monkeypatch.setattr(svcmod, 'fetch_invitations_by_inviter', raising_fetch)

    svc = InvitationService(db=None)
    res = await svc.get_invitations_by_inviter('u1')
    assert res['status_code'] == 500


@pytest.mark.asyncio
async def test_get_invitation_stats_happy_path(monkeypatch):
    async def fake_stats(db, user_id):
        return {'pending': 1, 'accepted': 2, 'expired': 0}

    monkeypatch.setattr(svcmod, 'get_invitation_stats_db', fake_stats)

    svc = InvitationService(db=None)
    res = await svc.get_invitation_stats('u1')
    assert res['status_code'] == 200
    assert res['data']['stats']['accepted'] == 2


@pytest.mark.asyncio
async def test_get_invitation_stats_error(monkeypatch):
    async def raising_stats(db, user_id):
        raise Exception('boom')

    monkeypatch.setattr(svcmod, 'get_invitation_stats_db', raising_stats)

    svc = InvitationService(db=None)
    res = await svc.get_invitation_stats('u1')
    assert res['status_code'] == 500
