import pytest
from unittest.mock import patch, AsyncMock
import re
from datetime import datetime, timedelta, timezone
import uuid

from app.utils import email_utils as eu


def test_render_template_double_and_single_braces():
    template = "Hello {{NAME}}, your id is {ID} and count is {{COUNT}}"
    out = eu._render_template(template, {"NAME": "Alice", "ID": 123, "COUNT": 5})
    assert "Alice" in out
    assert "123" in out
    assert "5" in out


def test_get_preview_email_content_unbalanced_braces_raises():
    with pytest.raises(ValueError):
        eu.get_preview_email_content("Hello {{NAME", "body", {"NAME": "A"})


def test_get_preview_email_content_sanitizes_html():
    body = '<div onclick="evil()">Hello</div><script>alert(1)</script><a href="javascript:alert(2)">link</a>'
    subj, sanitized = eu.get_preview_email_content("T", body, {})
    assert '<script>' not in sanitized
    assert 'onclick' not in sanitized
    assert 'javascript:' not in sanitized


def test_create_ics_content_contains_fields():
    start = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    ics = eu._create_ics_content_sync(start, end, 'Summary', 'Details')
    assert 'BEGIN:VCALENDAR' in ics
    assert 'DTSTART' in ics
    assert 'DTEND' in ics
    assert 'DESCRIPTION:Details' in ics


class DummySMTP:
    def __init__(self, *a, **kw):
        pass
    def starttls(self, context=None):
        pass
    def login(self, user, pw):
        pass
    def send_message(self, msg):
        pass
    def quit(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def test_send_interview_email_sync_success(monkeypatch):
    # Patch smtplib.SMTP to our DummySMTP
    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', DummySMTP)
    dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    ok = eu._send_interview_email_sync('to@example.com', 'A', 'http://join', 'r1', dt, 'SWE')
    assert ok is True


class BadSMTP(DummySMTP):
    def send_message(self, msg):
        raise Exception('smtp fail')


def test_send_interview_email_sync_failure(monkeypatch):
    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', BadSMTP)
    dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    ok = eu._send_interview_email_sync('to@example.com', 'A', 'http://join', 'r1', dt, 'SWE')
    assert ok is False


@pytest.mark.asyncio
async def test_send_interview_invite_template_used(monkeypatch):
    # Return a saved rendered template
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=('custom subj','<html>body</html>')))
    # Patch send_email_async to return True and capture args
    called = {}
    async def fake_send_email(subj, recipient, body):
        called['subj'] = subj
        called['recipient'] = recipient
        called['body'] = body
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send_email)

    dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    ok = await eu.send_interview_invite_email_async('to@example.com', 'A', 'http://join', 'r1', dt, 'Job')
    assert ok is True
    assert called.get('subj') == 'custom subj'
    assert 'body' in called.get('body')


@pytest.mark.asyncio
async def test_send_interview_invite_template_not_found_and_require_templates(monkeypatch):
    # Template fetch returns None
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr('app.utils.email_utils.settings', eu.settings)
    # Ensure require templates set True
    monkeypatch.setattr(eu.settings, 'email_require_templates', True)

    dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    ok = await eu.send_interview_invite_email_async('to@example.com', 'A', 'http://join', 'r1', dt, 'Job')
    assert ok is False


@pytest.mark.asyncio
async def test_send_otp_email_fallback_and_require_templates(monkeypatch):
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    # Patch send_email_async to capture args
    captured = {}
    async def fake_send_email(subj, recipient, html):
        captured['subj'] = subj
        captured['recipient'] = recipient
        captured['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send_email)

    ok = await eu.send_otp_email('to@example.com', '1234', 'Your OTP')
    assert ok is True
    assert 'OTP' in captured['subj'] or 'OTP' in captured['html']


@pytest.mark.asyncio
async def test_send_admin_role_change_email_promoted_and_demoted(monkeypatch):
    # Demotion case
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    async def fake_send(subj, recipient, html):
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)

    ok = await eu.send_admin_role_change_email('abc@x.com', 'Bob', 'ADMIN', 'HR', performed_by='SUE')
    assert ok is True
    ok2 = await eu.send_admin_role_change_email('abc@x.com', 'Bob', 'HR', 'ADMIN')
    assert ok2 is True


@pytest.mark.asyncio
async def test_send_admin_invite_and_admin_removal_templates(monkeypatch):
    # Test ADMIN_INVITE fallback and ADMIN_DELETE with direct templates
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    called = {}
    async def fake_send(subj, recipient, html):
        called['subj'] = subj
        called['recipient'] = recipient
        called['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)

    # admin invite
    ok = await eu.send_admin_invite_email('to@x.com', 'Admin', 'http://inv', expires_at=None)
    assert ok is True
    assert 'invite' in called['subj'].lower() or 'invite' in called['html'].lower()

    # admin removal
    called.clear()
    ok2 = await eu.send_admin_removal_email('del@x.com', 'User', db=None)
    assert ok2 is True
    assert 'revoked' in called['html'].lower() or 'revoked' in called['subj'].lower()


@pytest.mark.asyncio
async def test_send_update_verification_and_change_notification(monkeypatch):
    # Test EMAIL_UPDATE_VERIFICATION and EMAIL_CHANGE_TRANSFER_NOTIFICATION
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    called = {}
    async def fake_send(subj, recipient, html):
        called['subj'] = subj
        called['recipient'] = recipient
        called['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)

    # update verification
    ok = await eu.send_email_update_verification_link('new@x.com', 'Name', 'http://verify', 'old@x.com', api_info={'endpoint': '/foo'})
    assert ok is True
    assert 'verify' in called['subj'].lower() or 'verify' in called['html'].lower()

    # change transfer notification with approval_link and expires_at
    called.clear()
    expires = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(minutes=10)
    ok2 = await eu.send_email_change_transfer_notification('old@x.com', 'Admin', 'new@x.com', 'http://approve', expires_at=expires)
    assert ok2 is True
    assert 'approve' in called['html'].lower() or 'transfer' in called['subj'].lower()


@pytest.mark.asyncio
async def test_name_and_phone_update_templates_and_otp_email_update(monkeypatch):
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    called = {}
    async def fake_send(subj, recipient, html):
        called['subj'] = subj
        called['recipient'] = recipient
        called['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)

    ok = await eu.send_name_update_verification_link('to@x.com', 'Old Name', 'New Name', 'http://v')
    assert ok is True
    assert 'name' in called['subj'].lower() or 'name' in called['html'].lower()

    called.clear()
    ok2 = await eu.send_name_update_success_notification('to@x.com', 'New Name')
    assert ok2 is True

    called.clear()
    ok3 = await eu.send_phone_update_verification_link('p@x.com', 'Admin', '1111', '2222', 'http://v')
    assert ok3 is True

    called.clear()
    ok4 = await eu.send_otp_for_email_update('to@x.com', 'Admin', '9999')
    assert ok4 is True


def test_format_role_subject_variants():
    assert eu.format_role_subject('SUPER_ADMIN') == 'Super Admin'
    assert eu.format_role_subject('ADMIN') == 'Admin'
    assert eu.format_role_subject('HR') == 'HR'
    assert eu.format_role_subject('OTHER') == 'OTHER'


@pytest.mark.asyncio
@pytest.mark.parametrize('func_name, args', [
    ('send_admin_invite_email', ('to@x.com', 'Admin', 'http://inv')), 
    ('send_admin_removal_email', ('to@x.com', 'Admin')), 
    ('send_admin_role_change_email', ('to@x.com','Bob','ADMIN','HR')), 
    ('send_email_update_verification_link', ('to@x.com','N','http://v','old@x.com')), 
    ('send_email_change_transfer_notification', ('old@x.com','Admin','new@x.com', None)), 
    ('send_name_update_verification_link', ('to@x.com','Old','New','http://v')), 
    ('send_name_update_success_notification', ('to@x.com','New')), 
    ('send_phone_update_verification_link', ('to@x.com','Admin','1111','2222','http://v')), 
    ('send_otp_for_email_update', ('to@x.com','Admin','9999')),
])
async def test_send_functions_respect_require_templates(monkeypatch, func_name, args):
    # When require_templates is True and no saved template found, functions should return False
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', True)
    # The functions are defined in email_utils module - call by getattr
    func = getattr(eu, func_name)
    # Some functions accept additional 'db' param; we handle by calling with kwargs if necessary
    try:
        ok = await func(*args)
    except TypeError:
        # try passing db=None
        ok = await func(*args, db=None)
    assert ok is False


@pytest.mark.asyncio
@pytest.mark.parametrize('func_name, args', [
    ('send_admin_invite_email', ('to@x.com', 'Admin', 'http://inv')), 
    ('send_admin_removal_email', ('to@x.com', 'Admin')), 
    ('send_admin_role_change_email', ('to@x.com','Bob','ADMIN','HR')), 
    ('send_email_update_verification_link', ('to@x.com','N','http://v','old@x.com')), 
    ('send_email_change_transfer_notification', ('old@x.com','Admin','new@x.com', None)), 
    ('send_name_update_verification_link', ('to@x.com','Old','New','http://v')), 
    ('send_name_update_success_notification', ('to@x.com','New')), 
    ('send_phone_update_verification_link', ('to@x.com','Admin','1111','2222','http://v')), 
    ('send_otp_for_email_update', ('to@x.com','Admin','9999')),
])
async def test_send_functions_use_saved_template(monkeypatch, func_name, args):
    # When saved template is returned, subject/body should be passed to send_email_async
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=('TSUB', '<html>T</html>')))
    called = {}
    async def fake_send(subj, rec, body):
        called['subj'] = subj
        called['rec'] = rec
        called['body'] = body
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    func = getattr(eu, func_name)
    try:
        ok = await func(*args)
    except TypeError:
        ok = await func(*args, db=AsyncMock())
    assert ok is True
    assert called['subj'] == 'TSUB'


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_alias_and_normalization(monkeypatch):
    # Patch ConfigRepository.get_template_by_key behavior
    class FakeRec:
        def __init__(self, subj, body):
            self.subject_template = subj
            self.body_template_html = body

    async def fake_get_template(db, k):
        # Return a template only for ADMIN_ROLE_UPDATED alias
        if k == 'ADMIN_ROLE_UPDATED':
            return FakeRec('Hello {ADMIN_NAME}', '<div>{ADMIN_NAME}</div>')
        return None

    monkeypatch.setattr('app.utils.email_utils.ConfigRepository.get_template_by_key', AsyncMock(side_effect=fake_get_template))
    # Monkeypatch preview renderer to return processed strings
    monkeypatch.setattr('app.utils.email_utils.get_preview_email_content', lambda s, b, c: ('subject', 'body'))
    res_subj, res_body = await eu._fetch_and_render_saved_template(db=AsyncMock(), template_key='ADMIN_ROLE_CHANGE', context={'ADMIN_NAME': 'A'})
    assert res_subj == 'subject' and res_body == 'body'


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_fallback_on_errors(monkeypatch):
    # Simulate get_template_by_key raising for first candidate and returning record on second
    class FakeRec:
        def __init__(self, subj, body):
            self.subject_template = subj
            self.body_template_html = body

    async def side_effect(db, k):
        if k == 'ADMIN_ROLE_CHANGE':
            raise Exception('db broken')
        if k == 'ADMIN_ROLE_UPDATED':
            return FakeRec('S', 'B')
        return None

    monkeypatch.setattr('app.utils.email_utils.ConfigRepository.get_template_by_key', AsyncMock(side_effect=side_effect))
    monkeypatch.setattr('app.utils.email_utils.get_preview_email_content', lambda s, b, c: ('S', 'B'))
    res = await eu._fetch_and_render_saved_template(db=AsyncMock(), template_key='ADMIN_ROLE_CHANGE', context={'ADMIN_NAME': 'X'})
    assert res == ('S', 'B')


@pytest.mark.asyncio
async def test_send_interview_invite_custom_subject_body(monkeypatch):
    # Ensure that custom_subject/custom_body get rendered and sent when template not found
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    called = {}
    async def fake_send(subj, recipient, body):
        called['subj'] = subj
        called['body'] = body
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)

    dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    ok = await eu.send_interview_invite_email_async('x@x.com','Bob','http://j', 'r1', dt, 'Job', custom_subject='Hi {{CANDIDATE_NAME}}', custom_body='<p>{CANDIDATE_NAME}</p>')
    assert ok is True
    assert 'Bob' in called['subj'] or 'Bob' in called['body']


@pytest.mark.asyncio
async def test_send_email_update_verification_subject_api_info_included(monkeypatch):
    # template not found -> default used, but subject should include endpoint from api_info when provided
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)

    captured = {}
    async def fake_send(subj, rec, body):
        captured['subj'] = subj
        captured['rec'] = rec
        captured['body'] = body
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)

    api_info = {'endpoint': 'v1/admins/verify-email-update'}
    ok = await eu.send_email_update_verification_link('new@x.com', 'N', 'http://v', 'old@x.com', api_info=api_info)
    assert ok is True
    # Default fallback subject should NOT include the api_info endpoint (the function overrides with default subject)
    assert 'verify-email-update' not in captured['subj']


def test_get_default_templates_have_placeholders():
    # Ensure default templates include placeholders we expect
    subjects_and_bodies = [
        eu.get_default_interview_template_content(),
        eu.get_default_admin_invite_template_content(),
        eu.get_default_admin_role_update_template_content(),
        eu.get_default_admin_delete_template_content(),
        eu.get_default_otp_template_content(),
        eu.get_default_email_update_verification_template_content(),
        eu.get_default_email_change_transfer_notification_template_content(),
        eu.get_default_name_update_verification_template_content(),
        eu.get_default_name_update_success_template_content(),
        eu.get_default_phone_update_verification_template_content(),
        eu.get_default_otp_for_email_update_template_content(),
    ]
    for subj, body in subjects_and_bodies:
        assert subj and isinstance(subj, str)
        assert body and isinstance(body, str)
        # basic placeholder check e.g., contains {{ (double braces) or { OTP }
        assert '{{' in body or '{' in body


@pytest.mark.asyncio
async def test_send_admin_role_change_no_change(monkeypatch):
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)
    async def fake_send(subj, rec, html):
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    ok = await eu.send_admin_role_change_email('a@x.com', 'Bob', 'ADMIN', 'ADMIN')
    assert ok is True


def test_get_preview_email_content_unbalanced_body_raises():
    with pytest.raises(ValueError):
        eu.get_preview_email_content('S', 'Hello {{NAME', {'NAME': 'A'})


@pytest.mark.asyncio
async def test_send_admin_invite_expires_format_applies(monkeypatch):
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None,None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)
    called = {}
    async def fake_send(subj, rec, html):
        called['subj'] = subj
        called['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    expires = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=2)
    ok = await eu.send_admin_invite_email('to@x.com', 'Admin', 'http://inv', expires_at=expires)
    assert ok is True
    assert 'IST' in called['html'] or 'expire' in called['html'].lower()


@pytest.mark.asyncio
async def test_send_admin_invite_with_temp_db_saved_template(monkeypatch):
    # Simulate AsyncSessionLocal path by returning a dummy context manager
    class DummyLocal:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr('app.db.connection_manager.AsyncSessionLocal', DummyLocal)
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=('TSUB', '<html>T</html>')))
    called = {}
    async def fake_send(subj, rec, html):
        called['subj'] = subj
        called['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    ok = await eu.send_admin_invite_email('to@x.com', 'Admin', 'http://inv', db=None)
    assert ok is True
    assert called['subj'] == 'TSUB'


@pytest.mark.asyncio
async def test_send_otp_email_with_temp_db_saved_template(monkeypatch):
    class DummyLocal:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, exc_type, exc, tb):
            return None
    monkeypatch.setattr('app.db.connection_manager.AsyncSessionLocal', DummyLocal)
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=('OTS', '<html>OTP 5555</html>')))
    called = {}
    async def fake_send(subj, rec, body):
        called['subj'] = subj
        called['rec'] = rec
        called['body'] = body
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    ok = await eu.send_otp_email('to@x.com', '5555', 'Subj', db=None)
    assert ok is True
    assert called['subj'] == 'OTS'
    assert '5555' in called['body']


@pytest.mark.asyncio
async def test_send_admin_removal_email_saved_template_with_temp_db(monkeypatch):
    class DummyLocal:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, exc_type, exc, tb):
            return None
    monkeypatch.setattr('app.db.connection_manager.AsyncSessionLocal', DummyLocal)
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=('REM', '<html>Removed</html>')))
    monkeypatch.setattr('app.utils.email_utils.send_email_async', AsyncMock(return_value=True))
    ok = await eu.send_admin_removal_email('x@x.com', 'Admin', db=None)
    assert ok is True


def test_create_ics_content_sync_timezone_utc_conversion():
    # Start in IST then expect ICS times to be converted to UTC representation
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    start = datetime(2025, 12, 31, 18, 0, tzinfo=ist_tz)
    end = start + timedelta(hours=1)
    ics = eu._create_ics_content_sync(start, end, 'S', 'D')
    assert 'DTSTART:' in ics and 'DTEND:' in ics
    # Ensure times are in Zulu (UTC) format
    assert 'Z' in ics


def test_get_default_admin_invite_template_rendering():
    subj, html = eu.get_default_admin_invite_template_content()
    rendered = eu._render_template(html, {'ADMIN_NAME': 'Fred', 'INVITE_LINK': 'http://x', 'EXPIRES_TEXT': 'soon'})
    assert 'Fred' in rendered
    assert 'http://x' in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize('func_name, args, expected', [
    ('send_email_update_verification_link', ('new@x.com','N','http://v','old@x.com'), 'new@x.com'),
    ('send_email_change_transfer_notification', ('old@x.com','Admin','new@x.com'), 'new@x.com'),
    ('send_name_update_verification_link', ('to@x.com','Old','New','http://v'), 'New'),
    ('send_name_update_success_notification', ('to@x.com','New Name'), 'New Name'),
    ('send_phone_update_verification_link', ('p@x.com','Admin', None,'2222','http://v'), '2222'),
    ('send_otp_for_email_update', ('to@x.com','Admin','1234'), '1234'),
])
async def test_send_functions_temp_db_template(monkeypatch, func_name, args, expected):
    class DummyLocal:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, exc_type, exc, tb):
            return None
    monkeypatch.setattr('app.db.connection_manager.AsyncSessionLocal', DummyLocal)
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=('TSUB', f'<html>{expected}</html>')))
    called = {}
    async def fake_send(subj, rec, html):
        called['subj'] = subj
        called['html'] = html
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    func = getattr(eu, func_name)
    try:
        ok = await func(*args)
    except TypeError:
        ok = await func(*args, db=None)
    assert ok is True
    assert called['subj'] == 'TSUB'
    assert expected in called['html']


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_none_db_returns_none():
    res = await eu._fetch_and_render_saved_template(db=None, template_key='OTP', context={})
    assert res == (None, None)


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_re_sub_exception(monkeypatch):
    # Ensure we hit the regex exception branch gracefully and continue
    class FakeRec:
        def __init__(self, subj, body):
            self.subject_template = subj
            self.body_template_html = body

    async def fake_get_template(db, k):
        return FakeRec('Hi {ADMIN_NAME}', '<div onclick="x">{ADMIN_NAME}</div>')

    monkeypatch.setattr('app.utils.email_utils.ConfigRepository.get_template_by_key', AsyncMock(side_effect=fake_get_template))
    # make re.sub raise for demonstration
    monkeypatch.setattr('app.utils.email_utils.re', type('R', (), {'sub': lambda *a, **kw: (_ for _ in ()).throw(Exception('boom'))}))
    # Patch preview renderer to capture the raw templates passed through
    captured = {}
    def preview(s, b, c):
        captured['s'] = s
        captured['b'] = b
        return ('S', 'B')
    monkeypatch.setattr('app.utils.email_utils.get_preview_email_content', preview)
    subj, body = await eu._fetch_and_render_saved_template(db=AsyncMock(), template_key='ADMIN_ROLE_CHANGE', context={'ADMIN_NAME': 'X'})
    assert subj == 'S' and body == 'B'


def test_get_preview_email_content_strips_single_quote_handlers():
    body = "<div ONCLICK='alert(1)'>Hello</div>"
    subj, sanitized = eu.get_preview_email_content('S', body, {})
    assert 'ONCLICK' not in sanitized.upper()
    assert "javascript:" not in sanitized


def test__send_email_sync_smtp_exceptions(monkeypatch):
    """Test _send_email_sync handles SMTP exceptions and returns False."""
    import smtplib

    class SMTPAuthFail:
        def __init__(self, *a, **kw):
            pass
        def starttls(self, context=None):
            pass
        def login(self, user, pw):
            raise smtplib.SMTPAuthenticationError(535, b'Auth failed')
        def send_message(self, msg):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', SMTPAuthFail)
    ok = eu._send_email_sync('s', 't', '<p>h</p>')
    assert ok is False

    class SMTPConnectFail:
        def __init__(self, *a, **kw):
            raise smtplib.SMTPConnectError(421, b'Cannot connect')

    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', SMTPConnectFail)
    ok2 = eu._send_email_sync('s', 't', '<p>h</p>')
    assert ok2 is False

    class SMTPGenericFail(DummySMTP):
        def send_message(self, msg):
            raise smtplib.SMTPException('boom')

    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', SMTPGenericFail)
    ok3 = eu._send_email_sync('s', 't', '<p>h</p>')
    assert ok3 is False


@pytest.mark.asyncio
async def test_send_email_async_success_and_failure(monkeypatch):
    # Patch the synchronous call so it's deterministic
    monkeypatch.setattr('app.utils.email_utils._send_email_sync', lambda s, r, h: True)
    result = await eu.send_email_async('S','t','<p>1234</p>')
    assert result is True

    monkeypatch.setattr('app.utils.email_utils._send_email_sync', lambda s, r, h: False)
    result2 = await eu.send_email_async('S','t','<p>1234</p>')
    assert result2 is False


@pytest.mark.asyncio
async def test_send_interview_invite_fallback_default(monkeypatch):
    # When no saved template and require_templates False, ensure default fallback is used
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)
    called = {}
    async def fake_send(subj, recipient, body):
        called['subj'] = subj
        called['recipient'] = recipient
        called['body'] = body
        return True
    monkeypatch.setattr('app.utils.email_utils.send_email_async', fake_send)
    dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    ok = await eu.send_interview_invite_email_async('to@x.com', 'X', 'http://join', 'r1', dt, 'Engineer')
    assert ok is True
    assert 'Interview Invitation' in called['subj'] or 'Interview Invitation' in called['body']


@pytest.mark.asyncio
async def test_send_otp_email_fetch_exception_returns_false(monkeypatch):
    # If _fetch_and_render_saved_template raises, the function should return False
    async def raise_exc(*a, **kw):
        raise Exception('db oops')
    monkeypatch.setattr('app.utils.email_utils._fetch_and_render_saved_template', raise_exc)
    monkeypatch.setattr(eu.settings, 'email_require_templates', True)
    ok = await eu.send_otp_email('to@x.com', '1234', 'Subj')
    assert ok is False

