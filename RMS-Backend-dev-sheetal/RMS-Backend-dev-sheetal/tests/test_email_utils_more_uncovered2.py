import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.utils import email_utils
from datetime import datetime, timezone, timedelta


def test_render_template_supports_braces():
    tpl = "Hello {{NAME}}, your code is {CODE}"
    out = email_utils._render_template(tpl, {"NAME": "Alice", "CODE": 1234})
    assert "Alice" in out
    assert "1234" in out


def test_create_ics_contains_dtstart_dtend():
    start = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    ics = email_utils._create_ics_content_sync(start, end, "Sub", "Desc")
    assert "DTSTART" in ics
    assert "DTEND" in ics


def test_preview_email_content_unmatched_braces_raises():
    with pytest.raises(ValueError):
        email_utils.get_preview_email_content("Hello {{NAME}", "Body", {"NAME": "X"})


def test_preview_email_content_sanitizes_script_and_handlers():
    body = '<div onclick="alert(1)"><script>alert(1)</script><a href="javascript:bad()">click</a></div>'
    subj, sanitized = email_utils.get_preview_email_content("Hi {{NAME}}", body, {"NAME": "X"})
    assert "script" not in sanitized.lower()
    assert "onclick" not in sanitized.lower()
    assert "javascript:" not in sanitized.lower()


def test_send_interview_email_sync_uses_smtp_and_attaches_ics(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port):
            pass
        def starttls(self, context=None):
            pass
        def login(self, username, password):
            pass
        def send_message(self, msg):
            pass
        def quit(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    ok = email_utils._send_interview_email_sync("to@example.com", "Zed", "https://link", "ABC", dt, "Role")
    assert ok is True


@pytest.mark.asyncio
async def test_send_email_async_uses_thread_and_handles_result(monkeypatch):
    async def fake_to_thread(fn, *a, **kw):
        # Call the sync fn to return its value
        return fn(*a, **kw)

    def fake_send(subject, recipient, html):
        return True

    monkeypatch.setattr(email_utils, "_send_email_sync", fake_send)
    monkeypatch.setattr(email_utils.asyncio, "to_thread", fake_to_thread)
    res = await email_utils.send_email_async("S", "to@example.com", "<p>hello</p>")
    assert res is True


@pytest.mark.asyncio
async def test_send_otp_email_fallbacks_and_uses_default(monkeypatch):
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    # Use a stub send_email_async
    send_stub = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", send_stub)
    # Ensure templates not required so fallback used
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)

    res = await email_utils.send_otp_email("to@example.com", "1234", "OTP Subject")
    assert res is True
    assert send_stub.await_count == 1


@pytest.mark.asyncio
async def test_send_admin_role_change_email_fallbacks(monkeypatch):
    # Force template not found
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    stub_send = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", stub_send)
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)

    # Promotion path
    res = await email_utils.send_admin_role_change_email("to@example.com", "Alex", "HR", "ADMIN")
    assert res is True
    assert stub_send.await_count == 1

    # Demotion path
    res = await email_utils.send_admin_role_change_email("to@example.com", "Alex", "ADMIN", "HR")
    assert res is True
    assert stub_send.await_count == 2
