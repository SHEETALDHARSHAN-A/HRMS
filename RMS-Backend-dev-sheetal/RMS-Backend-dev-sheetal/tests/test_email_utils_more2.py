import asyncio
import smtplib
import pytest

from app.utils import email_utils as eu


def test__send_email_sync_various_exception_branches(monkeypatch):
    events = {}

    class ConnectBad:
        def __init__(self, server, port):
            pass

        def starttls(self, context=None):
            pass

        def login(self, user, pwd):
            raise smtplib.SMTPConnectError(421, b"connect")

        def send_message(self, msg):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(smtplib, 'SMTP', ConnectBad)
    assert eu._send_email_sync('s', 'r', '<p>x</p>') is False

    class GenericBad(ConnectBad):
        def login(self, user, pwd):
            return None

        def send_message(self, msg):
            raise Exception('boom')

    monkeypatch.setattr(smtplib, 'SMTP', GenericBad)
    assert eu._send_email_sync('s', 'r', '<p>x</p>') is False


@pytest.mark.asyncio
async def test_send_email_async_extracts_otp_and_returns(monkeypatch, caplog):
    # Patch _send_email_sync to return True so async wrapper succeeds
    def ok_send(subject, recipient, html):
        return True

    monkeypatch.setattr(eu, '_send_email_sync', ok_send)

    # Provide HTML that matches OTP regex used in send_email_async
    html = '<p style="font-size: 24px; font-weight: bold; color: #000; margin: 16px 0;">9999</p>'
    res = await eu.send_email_async('s', 'r', html)
    assert res is True


@pytest.mark.asyncio
async def test_send_email_update_verification_subject_api_info(monkeypatch):
    # Force no saved template and capture subject passed to send_email_async
    async def none_fetch(db, key, ctx):
        return (None, None)

    captured = {}

    async def fake_send(subject, recipient, html):
        captured['subject'] = subject
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)

    api_info = {'endpoint': '/api/verify'}
    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = False
    ok = await eu.send_email_update_verification_link('a@b.com', 'Admin', 'http://v', 'old@e', api_info=api_info, expires_at=None, db=None)
    assert ok is True
    eu.settings.email_require_templates = prev
    # The function may overwrite subject when falling back to defaults; ensure default subject is used
    assert captured['subject'].startswith('Action Required:')


@pytest.mark.asyncio
async def test_send_email_change_transfer_notification_includes_approval_block(monkeypatch):
    async def none_fetch(db, key, ctx):
        return (None, None)

    captured = {}

    async def fake_send(subject, recipient, html):
        captured['html'] = html
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)
    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = False

    ok = await eu.send_email_change_transfer_notification('old@e', 'Admin', 'new@e', approval_link='http://approve', expires_at=None, db=None)
    assert ok is True
    eu.settings.email_require_templates = prev
    assert 'http://approve' in captured['html']


@pytest.mark.asyncio
async def test_send_name_update_success_notification_fallback(monkeypatch):
    async def none_fetch(db, key, ctx):
        return (None, None)

    async def fake_send(subject, recipient, html):
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)

    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = False
    ok = await eu.send_name_update_success_notification('x@x.com', 'New Name', db=None)
    assert ok is True
    eu.settings.email_require_templates = prev
