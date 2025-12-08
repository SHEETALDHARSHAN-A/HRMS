import asyncio
from datetime import datetime, timedelta, timezone
import re
import smtplib

import pytest

from app.utils import email_utils as eu


def test_render_template_double_and_single_braces():
    tpl = "Hello {{NAME}}, your code is {CODE}"
    out = eu._render_template(tpl, {"NAME": "Alice", "CODE": 123})
    assert "Alice" in out
    assert "123" in out


def test_create_ics_content_sync_contains_expected_fields():
    start = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    ics = eu._create_ics_content_sync(start, end, "Interview", "Desc")
    assert "BEGIN:VCALENDAR" in ics
    assert "DTSTART:" in ics and "DTEND:" in ics
    assert "SUMMARY:Interview" in ics


def test_generate_default_interview_html_inserts_context():
    ctx = {
        "CANDIDATE_NAME": "Bob",
        "ROUND_NAME": "Phone",
        "JOB_TITLE": "Engineer",
        "NEXT_ROUND_NAME": "Onsite",
        "INTERVIEW_TIME": "01-01-2025 10:00 AM",
        "ROOM_CODE": "R123",
        "JOIN_URL": "http://join",
    }
    html = eu._generate_default_interview_html(ctx)
    assert "Bob" in html
    assert "Engineer" in html
    assert "R123" in html
    assert "http://join" in html


def test_get_preview_email_content_sanitizes_and_validates():
    # unmatched braces should raise
    with pytest.raises(ValueError):
        eu.get_preview_email_content("Hello {{NAME", "<p>Hi</p>", {"NAME": "A"})

    subject, body = eu.get_preview_email_content(
        "Hi {{NAME}}",
        '<div onclick="alert(1)"><script>alert(2)</script><a href="javascript:do()">link</a></div>',
        {"NAME": "A"},
    )
    assert "script" not in body.lower()
    assert "onclick" not in body.lower()
    assert "javascript" not in body.lower()


def test__send_interview_email_sync_success_and_failure(monkeypatch):
    # Replace smtplib.SMTP with a dummy that records calls
    events = {}

    class DummySMTP:
        def __init__(self, server, port):
            events['init'] = (server, port)

        def starttls(self, context=None):
            events['starttls'] = True

        def login(self, user, pwd):
            events['login'] = (user, pwd)

        def send_message(self, msg):
            events['sent'] = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    now = datetime.now(timezone.utc)
    ok = eu._send_interview_email_sync(
        to_email="a@b.com",
        candidate_name="X",
        interview_link="http://join",
        interview_token="R1",
        interview_datetime=now,
        job_title="Eng",
    )
    assert ok is True
    assert events.get('sent') is True

    # Now simulate an auth failure
    class BadSMTP(DummySMTP):
        def login(self, user, pwd):
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

    monkeypatch.setattr(smtplib, "SMTP", BadSMTP)
    bad = eu._send_interview_email_sync(
        to_email="a@b.com",
        candidate_name="X",
        interview_link="http://join",
        interview_token="R1",
        interview_datetime=now,
        job_title="Eng",
    )
    assert bad is False


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_saved_template_and_fallback(monkeypatch):
    # Patch _fetch_and_render_saved_template and send_email_async to avoid DB/SMTP
    async def fake_fetch(db, key, context):
        # return a filled template when key is INTERVIEW_INVITE
        if key == "INTERVIEW_INVITE":
            return ("Saved Subject", "<p>Saved Body</p>")
        return (None, None)

    async def fake_send_email(subject, recipient, html):
        return True

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', fake_fetch)
    monkeypatch.setattr(eu, 'send_email_async', fake_send_email)

    now = datetime.now(timezone.utc)
    # Provide a fake db object to avoid creating AsyncSessionLocal inside function
    res = await eu.send_interview_invite_email_async(
        to_email="x@x.com",
        candidate_name="C",
        interview_link="http://join",
        interview_token="R1",
        interview_datetime=now,
        job_title="Dev",
        db="FAKE_DB",
    )
    assert res is True

    # Now test fallback when saved template missing and template-only mode enabled
    async def none_fetch(db, key, context):
        return (None, None)

    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    # Enable template-only mode
    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = True
    res2 = await eu.send_interview_invite_email_async(
        to_email="x@x.com",
        candidate_name="C",
        interview_link="http://join",
        interview_token="R1",
        interview_datetime=now,
        job_title="Dev",
        db="FAKE_DB",
    )
    assert res2 is False
    eu.settings.email_require_templates = prev
