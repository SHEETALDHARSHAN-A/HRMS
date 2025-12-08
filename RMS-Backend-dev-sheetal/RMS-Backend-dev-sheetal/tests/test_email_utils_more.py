import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
import app.utils.email_utils as email_utils


@pytest.mark.asyncio
async def test_send_admin_invite_uses_saved_template(monkeypatch):
    # saved template present -> should call send_email_async with that subject
    async def fake_fetch(db, key, ctx):
        return "T_SUBJECT", "<p>rendered</p>"

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    monkeypatch.setattr(email_utils, "send_email_async", mock_send)

    res = await email_utils.send_admin_invite_email("a@b.com", "Admin", "https://x")
    assert res is True
    assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_send_admin_invite_fetch_raises_returns_false(monkeypatch):
    async def bad_fetch(db, key, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", bad_fetch)
    res = await email_utils.send_admin_invite_email("a@b.com", "Admin", "https://x")
    assert res is False


@pytest.mark.asyncio
async def test_send_name_update_success_uses_fallback_when_no_template(monkeypatch):
    async def fake_fetch(db, key, ctx):
        return None, None

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    monkeypatch.setattr(email_utils, "send_email_async", mock_send)
    email_utils.settings.email_require_templates = False

    res = await email_utils.send_name_update_success_notification("u@x.com", "New Name")
    assert res is True
    assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_send_email_async_when_sync_raises_returns_false(monkeypatch):
    def raise_send(subject, recipient, html):
        raise Exception("smtp fail")

    monkeypatch.setattr(email_utils, "_send_email_sync", raise_send)
    ok = await email_utils.send_email_async("s", "r@x.com", "<p>1</p>")
    assert ok is False


@pytest.mark.asyncio
async def test_send_otp_for_email_update_refuses_when_templates_required(monkeypatch):
    async def fake_fetch(db, key, ctx):
        return None, None

    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    email_utils.settings.email_require_templates = True
    res = await email_utils.send_otp_for_email_update("a@b.com", "Admin", "1234")
    assert res is False
import pytest
import smtplib
from unittest.mock import MagicMock
from types import SimpleNamespace
from datetime import datetime, timezone
from app.utils import email_utils


def test_default_template_getters_return_strings():
    getters = [
        email_utils.get_default_interview_template_content,
        email_utils.get_default_admin_invite_template_content,
        email_utils.get_default_admin_role_update_template_content,
        email_utils.get_default_admin_delete_template_content,
        email_utils.get_default_otp_template_content,
        email_utils.get_default_email_update_verification_template_content,
        email_utils.get_default_email_change_transfer_notification_template_content,
        email_utils.get_default_name_update_verification_template_content,
        email_utils.get_default_name_update_success_template_content,
        email_utils.get_default_phone_update_verification_template_content,
        email_utils.get_default_otp_for_email_update_template_content,
    ]

    for fn in getters:
        subj, body = fn()
        assert isinstance(subj, str)
        assert isinstance(body, str)
        assert len(subj) > 0
        assert len(body) > 0


def make_cm_with_behavior(on_login=None, on_send=None, on_enter=None):
    class CM:
        def __init__(self, server, port):
            pass

        def starttls(self, context=None):
            return None

        def login(self, username, password):
            if on_login:
                raise on_login

        def send_message(self, message):
            if on_send:
                raise on_send

        def __enter__(self):
            if on_enter:
                raise on_enter
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    return CM


def test_send_email_sync_auth_fail(monkeypatch):
    auth_exc = smtplib.SMTPAuthenticationError(535, b'Auth failed')
    CM = make_cm_with_behavior(on_login=auth_exc)
    monkeypatch.setattr(email_utils.smtplib, 'SMTP', CM)

    ok = email_utils._send_email_sync('s', 'r', '<p>h</p>')
    assert ok is False


def test_send_email_sync_connect_fail(monkeypatch):
    conn_exc = smtplib.SMTPConnectError(421, 'Cannot connect')
    CM = make_cm_with_behavior(on_enter=conn_exc)
    monkeypatch.setattr(email_utils.smtplib, 'SMTP', CM)

    ok = email_utils._send_email_sync('s', 'r', '<p>h</p>')
    assert ok is False


def test_send_email_sync_general_smtp_exception(monkeypatch):
    smtp_exc = smtplib.SMTPException('General')
    CM = make_cm_with_behavior(on_send=smtp_exc)
    monkeypatch.setattr(email_utils.smtplib, 'SMTP', CM)

    ok = email_utils._send_email_sync('s', 'r', '<p>h</p>')
    assert ok is False


def test_send_email_async_delegates(monkeypatch):
    # Patch the sync function to simulate success
    monkeypatch.setattr(email_utils, '_send_email_sync', lambda s, r, h: True)

    import asyncio

    res = asyncio.get_event_loop().run_until_complete(
        email_utils.send_email_async('subj', 'to@x', '<p>body</p>')
    )
    assert res is True


def test_render_and_preview_and_ics(monkeypatch):
    # Render templates
    r = email_utils._render_template('Hi {{NAME}} and {ROLE}', {'NAME': 'Alice', 'ROLE': 'Dev'})
    assert 'Alice' in r and 'Dev' in r

    # Preview sanitization: script and onload removed
    subject = 'Hi {{NAME}}'
    body = '<p>Hello</p><script>alert(1)</script><img onload="evil()">'
    sub, b = email_utils.get_preview_email_content(subject, body, {'NAME': 'X'})
    assert 'script' not in b
    assert 'onload' not in b

    # Unmatched braces: should raise
    with pytest.raises(ValueError):
        email_utils.get_preview_email_content('Hi {{NAME', '<p></p>', {})

    # ICS generation includes fields
    from datetime import datetime, timedelta, timezone
    s = datetime.now(timezone.utc)
    e = s + timedelta(hours=1)
    ics = email_utils._create_ics_content_sync(s, e, 'Sub', 'Desc')
    assert 'SUMMARY:Sub' in ics
    assert 'DESCRIPTION:Desc' in ics


@pytest.mark.asyncio
async def test_send_interview_invite_and_otp_and_admin_removal(monkeypatch):
    # Setup a stub for _fetch_and_render_saved_template
    async def fake_fetch(db, key, ctx):
        if key == 'INTERVIEW_INVITE':
            return ('Rendered Sub', '<p>Body</p>')
        if key == 'OTP':
            return (None, None)
        return (None, None)

    monkeypatch.setattr(email_utils, '_fetch_and_render_saved_template', fake_fetch)
    # Stub send_email_async to always succeed
    async def ok_send(s, r, b):
        return True

    monkeypatch.setattr(email_utils, 'send_email_async', ok_send)

    from datetime import datetime, timezone
    dt = datetime.now(timezone.utc)

    # When saved template exists, should use it and return True
    res = await email_utils.send_interview_invite_email_async('a@b', 'Name', 'link', 'ROOM', dt, 'J')
    assert res is True

    # OTP: _fetch returns none and settings.email_require_templates True -> should be False
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', True)
    res = await email_utils.send_otp_email('a@b', '1234', 'subject')
    assert res is False

    # OTP: with templates not required -> fallback using default and send succeeds
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', False)
    res = await email_utils.send_otp_email('a@b', '1234', 'subject')
    assert res is True

    # Admin removal: template missing and require_templates True => refuse
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', True)
    res = await email_utils.send_admin_removal_email('a@b', 'Admin')
    assert res is False

    # Admin removal: require_templates False -> fallback and sent
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', False)
    res = await email_utils.send_admin_removal_email('a@b', 'Admin')
    assert res is True


def test_format_role_subject_and_role_change(monkeypatch):
    assert email_utils.format_role_subject('SUPER_ADMIN') == 'Super Admin'
    assert email_utils.format_role_subject('ADMIN') == 'Admin'
    assert email_utils.format_role_subject('HR') == 'HR'
    assert email_utils.format_role_subject('UNKNOWN') == 'UNKNOWN'


@pytest.mark.asyncio
async def test_send_admin_invite_and_role_change_and_update(monkeypatch):
    # Patch send_email_async to record calls
    called = {'count': 0}

    async def ok_send(s, r, b):
        called['count'] += 1
        return True

    monkeypatch.setattr(email_utils, 'send_email_async', ok_send)

    # admin invite: saved template present
    async def fetch_invite(db, key, ctx):
        return ('Subject', '<p>body</p>')

    monkeypatch.setattr(email_utils, '_fetch_and_render_saved_template', fetch_invite)
    from datetime import datetime, timezone
    res = await email_utils.send_admin_invite_email('a@b', 'Admin', 'link', datetime.now(timezone.utc))
    assert res is True

    # admin invite: missing template & required -> fail
    async def none_fetch(db, key, ctx):
        return (None, None)
    monkeypatch.setattr(email_utils, '_fetch_and_render_saved_template', none_fetch)
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', True)
    res = await email_utils.send_admin_invite_email('a@b', 'Admin', 'link')
    assert res is False
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', False)

    # admin role change: promotion/demotion path
    monkeypatch.setattr(email_utils, '_fetch_and_render_saved_template', none_fetch)
    res = await email_utils.send_admin_role_change_email('a@b', 'Admin', 'ADMIN', 'SUPER_ADMIN')
    assert res is True
    res = await email_utils.send_admin_role_change_email('a@b', 'Admin', 'SUPER_ADMIN', 'ADMIN')
    assert res is True

    # email update verification link: missing template & required -> fail
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', True)
    res = await email_utils.send_email_update_verification_link('a@b', 'Admin', 'link', 'old@a')
    assert res is False
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', False)
    res = await email_utils.send_email_update_verification_link('a@b', 'Admin', 'link', 'old@a')
    assert res is True

    # email change transfer notification
    res = await email_utils.send_email_change_transfer_notification('old@a', 'Admin', 'new@a')
    assert res is True

    # name update verification + success + phone update
    res = await email_utils.send_name_update_verification_link('a@b', 'Old', 'New', 'link')
    assert res is True
    res = await email_utils.send_name_update_success_notification('a@b', 'New', 'Old')
    assert res is True
    res = await email_utils.send_phone_update_verification_link('a@b', 'Admin', 'old-phone', 'new-phone', 'link')
    assert res is True

    # OTP for email update
    res = await email_utils.send_otp_for_email_update('a@b', 'CODE', 'link')
    assert res is True


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_behaviours(monkeypatch):
    # Simulate ConfigRepository.get_template_by_key returning a record with single-brace placeholders
    class Record:
        def __init__(self, subj, body):
            self.subject_template = subj
            self.body_template_html = body

    async def fake_get_template(db, key):
        return Record('Hi {NAME}', '<p>Body {NAME}</p>')

    monkeypatch.setattr(email_utils.ConfigRepository, 'get_template_by_key', fake_get_template)

    subject, body = await email_utils._fetch_and_render_saved_template(SimpleNamespace(), 'OTP', {'NAME': 'Alice'})
    assert 'Alice' in subject
    assert 'Alice' in body

    # Not found
    async def fake_none(db, key):
        return None

    monkeypatch.setattr(email_utils.ConfigRepository, 'get_template_by_key', fake_none)
    subj, body = await email_utils._fetch_and_render_saved_template(SimpleNamespace(), 'OTP', {'NAME': 'X'})
    assert subj is None and body is None

    # If preview rendering throws, the error should propagate
    async def bad_template(db, key):
        return Record('Hi {{BAR', '<p>broken</p>')
    monkeypatch.setattr(email_utils.ConfigRepository, 'get_template_by_key', bad_template)
    with pytest.raises(ValueError):
        await email_utils._fetch_and_render_saved_template(SimpleNamespace(), 'OTP', {'NAME': 'X'})


@pytest.mark.asyncio
async def test_fetch_saved_template_alias_and_normalization(monkeypatch):
    # Simulate get_template_by_key returning only for alias 'ADMIN_INVITATION'
    class R:
        def __init__(self, subj, body):
            self.subject_template = subj
            self.body_template_html = body

    async def fake_get_template(db, key):
        if key == 'ADMIN_INVITATION':
            return R('Hi {ADMIN_NAME}', '<p>Welcome {ADMIN_NAME}</p>')
        return None

    monkeypatch.setattr(email_utils.ConfigRepository, 'get_template_by_key', fake_get_template)

    s, b = await email_utils._fetch_and_render_saved_template(SimpleNamespace(), 'ADMIN_INVITE', {'ADMIN_NAME': 'Paul'})
    assert 'Paul' in s and 'Paul' in b

    # Simulate regex.sub raising -> substitution should be skipped gracefully
    orig_sub = email_utils.re.sub
    def conditional_sub(pattern, repl, string):
        # If the pattern is the single-brace normalization pattern, raise
        if isinstance(pattern, str) and '([A-Z0-9_]+)' in pattern:
            raise Exception('bad regex')
        return orig_sub(pattern, repl, string)
    monkeypatch.setattr(email_utils.re, 'sub', conditional_sub, raising=True)

    async def fake_template2(db, key):
        return R('Hi {ADMIN_NAME}', '<p>Welcome {ADMIN_NAME}</p>')
    monkeypatch.setattr(email_utils.ConfigRepository, 'get_template_by_key', fake_template2)

    s2, b2 = await email_utils._fetch_and_render_saved_template(SimpleNamespace(), 'ADMIN_INVITE', {'ADMIN_NAME': 'Kat'})
    assert 'Kat' in s2 and 'Kat' in b2


@pytest.mark.asyncio
async def test_interview_invite_custom_fallback(monkeypatch):
    # Simulate fetch raising to ensure wrapper falls back
    async def raising_fetch(db, key, ctx):
        raise Exception('boom')
    monkeypatch.setattr(email_utils, '_fetch_and_render_saved_template', raising_fetch)

    # Patch send_email_async to capture subject/body
    captured = {}
    async def capture_send(s, r, b):
        captured['s'] = s
        captured['r'] = r
        captured['b'] = b
        return True

    monkeypatch.setattr(email_utils, 'send_email_async', capture_send)

    dt = datetime.now(timezone.utc)
    # If fetch raises, the wrapper returns False (no fallback)
    res = await email_utils.send_interview_invite_email_async('r@t', 'Name', 'url', 'ROOM', dt, 'Job', custom_subject='Hello {CANDIDATE_NAME}', custom_body='<p>{CANDIDATE_NAME}</p>')
    assert res is False

    # If fetch returns None (not found) and templates not required, custom subject/body used
    async def none_fetch(db, key, ctx):
        return (None, None)
    monkeypatch.setattr(email_utils, '_fetch_and_render_saved_template', none_fetch)
    monkeypatch.setattr(email_utils.settings, 'email_require_templates', False)
    res = await email_utils.send_interview_invite_email_async('r@t', 'Name', 'url', 'ROOM', dt, 'Job', custom_subject='Hello {CANDIDATE_NAME}', custom_body='<p>{CANDIDATE_NAME}</p>')
    assert res is True
    assert 'Hello' in captured['s']
    assert 'Name' in captured['b']
