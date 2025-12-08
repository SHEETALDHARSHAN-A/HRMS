import pytest
import asyncio
from datetime import datetime, timezone, timedelta
import app.utils.email_utils as email_utils


def test_render_template_replaces_placeholders():
    tpl = "Hello {{NAME}}, age {AGE}"
    out = email_utils._render_template(tpl, {"NAME": "Alice", "AGE": 30})
    assert "Alice" in out
    assert "30" in out


def test_get_preview_email_content_unbalanced_braces_raises():
    with pytest.raises(ValueError):
        email_utils.get_preview_email_content("Hello {{NAME", "<p>Hi</p>", {"NAME": "X"})


def test_get_preview_email_content_sanitizes_html():
    subject, body = email_utils.get_preview_email_content(
        "Hi {{NAME}}",
        '<script>alert(1)</script><p onclick="do()">Hello</p>',
        {"NAME": "Bob"},
    )
    assert "<script" not in body.lower()
    assert "onclick" not in body.lower()


def test_create_ics_content_sync_contains_fields():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    ics = email_utils._create_ics_content_sync(start, end, "Subject", "Description")
    assert "BEGIN:VEVENT" in ics
    assert "DTSTART" in ics
    assert "DTEND" in ics


@pytest.mark.asyncio
async def test_send_email_async_success(monkeypatch):
    # Patch the synchronous sender to avoid real SMTP
    monkeypatch.setattr(email_utils, "_send_email_sync", lambda s, r, h: True)
    ok = await email_utils.send_email_async("S", "a@b.com", "<p>ok</p>")
    assert ok is True


@pytest.mark.asyncio
async def test_send_otp_email_fallback_and_requirements(monkeypatch):
    # Make fetch template return None (no saved template)
    async def fake_fetch(db, key, ctx):
        return None, None

    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    monkeypatch.setattr(email_utils, "_send_email_sync", lambda s, r, h: True)

    # When templates are not required, should fall back and send
    monkeypatch.setattr(email_utils, "settings", email_utils.settings)
    email_utils.settings.email_require_templates = False
    res = await email_utils.send_otp_email("x@y.com", "1234", "OTP test", db=None)
    assert res is True

    # When templates are required, send_otp_email should refuse
    email_utils.settings.email_require_templates = True
    res2 = await email_utils.send_otp_email("x@y.com", "1234", "OTP test", db=None)
    assert res2 is False


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_no_db_returns_none():
    rs = await email_utils._fetch_and_render_saved_template(None, "ANY", {})
    assert rs == (None, None)
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.utils import email_utils


def test_create_ics_content_sync_basic():
    start = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    content = email_utils._create_ics_content_sync(start, end, "Interview for X", "Details")
    assert "BEGIN:VCALENDAR" in content
    assert "DTSTAMP" in content
    assert "SUMMARY:Interview for X" in content


class DummySMTP:
    """A very small dummy SMTP replacement that emulates the context manager used in the module."""
    def __init__(self, server, port):
        self.server = server
        self.port = port

    def starttls(self, context=None):
        # no-op for tests
        return None

    def login(self, username, password):
        # emulate a successful auth
        return None

    def send_message(self, msg):
        # record a simple attribute so tests can assert the call
        self.sent = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_send_interview_email_sync_uses_smtp(monkeypatch):
    # Replace smtplib.SMTP with our DummySMTP to avoid network calls
    monkeypatch.setattr(email_utils.smtplib, "SMTP", DummySMTP)

    now = datetime.now(timezone.utc)
    ok = email_utils._send_interview_email_sync(
        to_email="user@example.com",
        candidate_name="Alice",
        interview_link="https://meet.example/room",
        interview_token="ROOM123",
        interview_datetime=now,
        job_title="Engineer",
    )

    assert ok is True


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_threads_to_sync(monkeypatch):
    # Ensure the underlying SMTP usage is mocked; the async wrapper should return True
    monkeypatch.setattr(email_utils.smtplib, "SMTP", DummySMTP)
    # Avoid DB access for templates: force no saved template and fallback behavior
    async def fake_fetch(db, key, ctx):
        return None, None
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    email_utils.settings.email_require_templates = False

    now = datetime.now(timezone.utc)
    res = await email_utils.send_interview_invite_email_async(
        to_email="user2@example.com",
        candidate_name="Bob",
        interview_link="https://meet.example/room2",
        interview_token="ABC",
        interview_datetime=now,
        job_title="Designer",
    )

    assert res is True


@pytest.mark.asyncio
async def test_send_email_async_logs_and_calls_send(monkeypatch):
    # Patch the synchronous _send_email_sync to avoid real SMTP and to ensure it's called
    called = {"count": 0}

    def fake_send(subject, recipient, html):
        called["count"] += 1
        # return True as if the SMTP send succeeded
        return True

    monkeypatch.setattr(email_utils, "_send_email_sync", fake_send)

    # Provide HTML that includes the OTP pattern the function extracts for logging
    html = '<p style="font-size: 24px; font-weight: bold;">123456</p>'
    ok = await email_utils.send_email_async("Subj", "me@example.com", html)
    assert ok is True
    assert called["count"] == 1


def test_format_role_subject_known_values():
    assert email_utils.format_role_subject("SUPER_ADMIN") == "Super Admin"
    assert email_utils.format_role_subject("ADMIN") == "Admin"
    assert email_utils.format_role_subject("HR") == "HR"


@pytest.mark.asyncio
async def test_send_admin_role_change_email_promoted_and_demoted(monkeypatch):
    # Capture the subject passed to send_email_async
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", mock_send)
    # Avoid DB access for templates
    async def fake_fetch(db, key, ctx):
        return None, None
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    email_utils.settings.email_require_templates = False

    # Case: promoted
    await email_utils.send_admin_role_change_email("u@example.com", "User", "HR", "ADMIN", performed_by="X")
    assert mock_send.await_count >= 1
    called_args = mock_send.await_args_list[-1][0]
    assert "Promoted" in called_args[0] or "Administrator Role" in called_args[0]

    # Case: demoted
    await email_utils.send_admin_role_change_email("u@example.com", "User", "ADMIN", "HR")
    called_args = mock_send.await_args_list[-1][0]
    # Subject should indicate Demoted or Updated
    assert any(x in called_args[0] for x in ("Demoted", "Updated", "Administrator Role"))


@pytest.mark.asyncio
async def test_templates_call_send_email_async(monkeypatch):
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", mock_send)
    # Avoid DB template lookups which try to use real DB in CI/local
    async def fake_fetch(db, key, ctx):
        return None, None
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", fake_fetch)
    email_utils.settings.email_require_templates = False

    # A few representative template functions should call send_email_async and return True
    assert await email_utils.send_otp_email("a@b.com", "999999", "OTP Subject") is True
    assert await email_utils.send_admin_invite_email("a@b.com", "Admin", "https://link") is True
    assert await email_utils.send_name_update_verification_link("a@b.com", "Old Name", "New Name", "https://v") is True

    assert await email_utils.send_phone_update_verification_link("a@b.com", "Admin", None, "9876543210", "https://v") is True

def test_render_template_double_and_single_braces():
    template = "Hello {{NAME}}, your code is {CODE} and id {{ID}}"
    context = {"NAME": "Alice", "CODE": 1234, "ID": "xyz"}

    rendered = email_utils._render_template(template, context)

    assert "Alice" in rendered
    assert "1234" in rendered
    assert "xyz" in rendered
    assert "{{" not in rendered and "}}" not in rendered

def test_render_template_unknown_keys_unchanged():
    template = "Hello {{NAME}}, unknown {{UNKNOWN}}"
    context = {"NAME": "Bob"}
    rendered = email_utils._render_template(template, context)

    # Known key replaced, unknown placeholder remains as-is
    assert "Bob" in rendered
    assert "{{UNKNOWN}}" in rendered

def test_generate_default_interview_html_inserts_context_values():
    ctx = {
        "CANDIDATE_NAME": "Sam",
        "ROUND_NAME": "Phone Screen",
        "JOB_TITLE": "Software Engineer",
        "NEXT_ROUND_NAME": "Onsite",
        "INTERVIEW_TIME": "01-01-2025 05:30 PM",
        "ROOM_CODE": "ROOM42",
        "JOIN_URL": "https://meet.example/room42",
    }

    html = email_utils._generate_default_interview_html(ctx)

    assert "Sam" in html
    assert "Phone Screen" in html
    assert "Software Engineer" in html
    assert "Onsite" in html
    assert "01-01-2025 05:30 PM" in html
    assert "ROOM42" in html
    assert "https://meet.example/room42" in html

def test_send_interview_email_sync_failure_on_send(monkeypatch):
    # emulate SMTP that raises on send_message
    class BadSMTP:
        def __init__(self, server, port):
            pass

        def starttls(self, context=None):
            return None

        def login(self, username, password):
            return None

        def send_message(self, msg):
            raise Exception("send failed")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(email_utils.smtplib, "SMTP", BadSMTP)

    now = datetime.now(timezone.utc)
    ok = email_utils._send_interview_email_sync(
        to_email="user-fail@example.com",
        candidate_name="FailCase",
        interview_link="https://meet.example/room",
        interview_token="ROOM999",
        interview_datetime=now,
        job_title="Engineer",
    )

    assert ok is False
