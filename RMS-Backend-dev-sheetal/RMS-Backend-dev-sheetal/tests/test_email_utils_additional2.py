import asyncio
from datetime import datetime, timezone
import pytest

from types import SimpleNamespace

from app.utils import email_utils as eu


def test_format_role_subject_known_and_unknown():
    assert eu.format_role_subject('SUPER_ADMIN') == 'Super Admin'
    assert eu.format_role_subject('ADMIN') == 'Admin'
    assert eu.format_role_subject('HR') == 'HR'
    assert eu.format_role_subject('CUSTOM') == 'CUSTOM'


def test__fetch_and_render_saved_template_with_record(monkeypatch):
    # Create a fake DB and fake record
    class FakeRecord:
        subject_template = 'Hello {ADMIN_NAME}'
        body_template_html = '<p>Welcome {ADMIN_NAME}</p>'

    async def fake_get_template(db, key):
        return FakeRecord()

    monkeypatch.setattr(eu.ConfigRepository, 'get_template_by_key', fake_get_template)

    # Use a fake AsyncSession (truthy) and ensure rendering normalizes braces
    rendered_subject, rendered_body = asyncio.get_event_loop().run_until_complete(
        eu._fetch_and_render_saved_template(db=True, template_key='ADMIN_INVITE', context={'ADMIN_NAME': 'Z'}))

    assert 'Hello' in rendered_subject
    assert 'Welcome' in rendered_body


def test__fetch_and_render_saved_template_no_db_or_no_record(monkeypatch):
    async def fake_none(db, key):
        return None

    monkeypatch.setattr(eu.ConfigRepository, 'get_template_by_key', fake_none)

    res = asyncio.get_event_loop().run_until_complete(
        eu._fetch_and_render_saved_template(db=True, template_key='NOT_EXIST', context={}))
    assert res == (None, None)


@pytest.mark.asyncio
async def test_send_email_async_handles_exception(monkeypatch):
    # Make the underlying sync function raise when called
    def bad_send(subject, recipient, html):
        raise RuntimeError('boom')

    monkeypatch.setattr(eu, '_send_email_sync', bad_send)

    res = await eu.send_email_async('s', 'r', '<p>x</p>')
    assert res is False


@pytest.mark.asyncio
async def test_send_otp_email_fallback_and_template_only(monkeypatch):
    # Case 1: template present -> send_email_async called
    async def present(db, key, ctx):
        return ('S', '<p>B</p>')

    async def fake_send(subject, recipient, html):
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', present)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)

    ok = await eu.send_otp_email('a@b.com', '1234', 'subj', db='DB')
    assert ok is True

    # Case 2: no template and template-only enabled -> False
    async def none_fetch(db, key, ctx):
        return (None, None)

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = True
    ok2 = await eu.send_otp_email('a@b.com', '2222', 'subj', db='DB')
    assert ok2 is False
    eu.settings.email_require_templates = prev


@pytest.mark.asyncio
async def test_send_admin_invite_email_fallback(monkeypatch):
    async def none_fetch(db, key, ctx):
        return (None, None)

    async def fake_send(subject, recipient, html):
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)

    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = False
    ok = await eu.send_admin_invite_email('x@x.com', 'Admin', 'http://inv', expires_at=None, db=None)
    assert ok is True
    eu.settings.email_require_templates = prev


@pytest.mark.asyncio
async def test_send_admin_role_change_email_promoted_and_demoted(monkeypatch):
    # Simulate saved template path
    async def present(db, key, ctx):
        return ('S', '<p>B</p>')

    async def fake_send(subject, recipient, html):
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', present)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)

    ok = await eu.send_admin_role_change_email('a@b.com', 'Name', old_role='ADMIN', new_role='SUPER_ADMIN', performed_by='Sys', db='DB')
    assert ok is True

    # Test demoted path (no template)
    async def none_fetch(db, key, ctx):
        return (None, None)

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = False
    ok2 = await eu.send_admin_role_change_email('a@b.com', None, old_role='SUPER_ADMIN', new_role='HR', performed_by=None, db=None)
    assert ok2 is True
    eu.settings.email_require_templates = prev
