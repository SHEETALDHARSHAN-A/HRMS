import re
import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import smtplib

from app.utils.email_utils import (
    _render_template,
    get_preview_email_content,
    _create_ics_content_sync,
    _send_email_sync,
    get_default_admin_invite_template_content,
)


def test_render_template_double_and_single_braces():
    tpl = "Hello {{NAME}}, your code is {CODE} and number {{NUM}}"
    out = _render_template(tpl, {"NAME": "Alice", "CODE": "X1", "NUM": 42})
    assert "Alice" in out
    assert "X1" in out
    assert "42" in out


def test_get_preview_email_content_sanitizes_and_renders():
    subject = "Welcome {{USER}}"
    body = '<div onclick="doBad()">Hi {{USER}}<script>alert(1)</script><a href="javascript:evil()">link</a></div>'
    rendered_subject, rendered_body = get_preview_email_content(subject, body, {"USER": "Bob"})

    assert "Bob" in rendered_subject
    assert "Bob" in rendered_body
    # script tag removed
    assert "script" not in rendered_body.lower()
    # javascript: links converted or removed
    assert "javascript:" not in rendered_body.lower()
    # inline event handler removed
    assert "onclick" not in rendered_body.lower()


def test_get_preview_email_content_unmatched_braces_raises():
    subject = "Bad {{MISSING"
    body = "Good"
    with pytest.raises(ValueError):
        get_preview_email_content(subject, body, {})


def test_create_ics_content_contains_dt_and_uid():
    start = datetime(2025, 11, 17, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    content = _create_ics_content_sync(start, end, "Summary", "Desc")
    assert "DTSTART" in content
    assert "DTEND" in content
    assert "UID:" in content


class DummySMTP:
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.started = False
        self.logged_in = False
        self.sent = False

    def starttls(self, context=None):
        self.started = True

    def login(self, user, pw):
        if user == "bad":
            raise smtplib.SMTPAuthenticationError(535, b'Auth failed')
        self.logged_in = True

    def send_message(self, msg):
        if "fail-send" in msg.as_string():
            raise smtplib.SMTPException("send failed")
        self.sent = True

    def quit(self):
        return None

    # context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_send_email_sync_success(monkeypatch):
    # patch SMTP class
    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', DummySMTP)
    ok = _send_email_sync("Hi", "to@example.com", "<p>ok</p>")
    assert ok is True


def test_send_email_sync_failure(monkeypatch):
    # patch SMTP to raise on login
    def bad_constructor(server, port):
        return DummySMTP(server, port)

    monkeypatch.setattr('app.utils.email_utils.smtplib.SMTP', bad_constructor)

    # Force authentication failure by setting username to 'bad' temporarily
    import app.utils.email_utils as eu
    old_user = eu.SMTP_USERNAME
    eu.SMTP_USERNAME = 'bad'
    try:
        ok = _send_email_sync("Hi", "to@example.com", "<p>ok</p>")
        assert ok is False
    finally:
        eu.SMTP_USERNAME = old_user


def test_get_default_admin_invite_template_content_contains_placeholders():
    subj, body = get_default_admin_invite_template_content()
    # The f-string uses double-brace in source to output single braces in result
    assert "{ADMIN_NAME}" in body
    assert "{INVITE_LINK}" in body
