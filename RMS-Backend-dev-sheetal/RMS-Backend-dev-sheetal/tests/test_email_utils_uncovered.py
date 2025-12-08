import pytest
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import uuid
import re

from app.utils import email_utils as eu


def test_render_template_double_and_single_brace():
    tpl = "Hello {{NAME}} and {NAME}"
    res = eu._render_template(tpl, {"NAME": "Alice"})
    assert "Alice" in res


def test_get_preview_email_content_sanitizes_script_and_onclick():
    subject = "Title"
    body = '<div onclick="alert(1)"><script>alert(2)</script>Hi</div><a href="javascript:evil()">link</a>'
    subj, body_out = eu.get_preview_email_content(subject, body, {"NAME": "Bob"})
    assert "script" not in body_out.lower()
    assert "onclick" not in body_out.lower()
    assert "javascript:" not in body_out.lower()


def test_create_ics_content_sync_contains_summary_and_times():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    content = eu._create_ics_content_sync(start, end, "Subj", "Desc")
    assert "BEGIN:VCALENDAR" in content
    assert "SUMMARY:Subj" in content
    assert "DESCRIPTION:Desc" in content


def test_generate_default_interview_html_contains_context_values():
    ctx = {"CANDIDATE_NAME": "Z", "ROUND_NAME": "Round1", "JOB_TITLE": "Dev", "NEXT_ROUND_NAME": "Final", "INTERVIEW_TIME": "SomeTime", "ROOM_CODE": "R1", "JOIN_URL": "http://x"}
    html = eu._generate_default_interview_html(ctx)
    assert "Z" in html
    assert "Round1" in html
    assert "Dev" in html


def test__send_email_sync_smtp_exceptions(monkeypatch):
    # Replace SMTP to simulate auth error
    class FakeSMTP:
        def __init__(self, *a, **kw):
            pass
        def starttls(self, context=None):
            return None
        def login(self, u, p):
            raise eu.smtplib.SMTPAuthenticationError(535, b'auth failed')
        def send_message(self, msg):
            return None
        def quit(self):
            return None
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(eu.smtplib, 'SMTP', FakeSMTP)
    ok = eu._send_email_sync('s', 'r', '<p>h</p>')
    assert ok is False


@pytest.mark.asyncio
async def test_send_interview_invite_saved_template_and_fallback(monkeypatch):
    # Prepare context
    dt = datetime.now(timezone.utc) + timedelta(days=1)

    # Case 1: saved template exists
    async def async_fetch(db, key, ctx):
        return ('S', '<p>body</p>')
    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', async_fetch)
    async def async_send(s, r, h):
        return True
    monkeypatch.setattr(eu, 'send_email_async', async_send)
    ok = await eu.send_interview_invite_email_async('t@x', 'C', 'http://j', 'R1', dt, 'Dev', db=SimpleNamespace())
    assert ok is True

    # Case 2: template missing and settings require templates -> refuse
    async def async_fetch_none(db, key, ctx):
        return (None, None)
    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', async_fetch_none)
    monkeypatch.setattr(eu.settings, 'email_require_templates', True)
    ok2 = await eu.send_interview_invite_email_async('t@x', 'C', 'http://j', 'R1', dt, 'Dev', None)
    assert ok2 is False

    # Case 3: template missing, fallback to default works
    monkeypatch.setattr(eu.settings, 'email_require_templates', False)
    sent = []
    async def fake_send(subject, recipient, html):
        sent.append((subject, recipient))
        return True
    monkeypatch.setattr(eu, 'send_email_async', fake_send)
    ok3 = await eu.send_interview_invite_email_async('t@x', 'C', 'http://j', 'R1', dt, 'Dev', None)
    assert ok3 is True
    assert sent
