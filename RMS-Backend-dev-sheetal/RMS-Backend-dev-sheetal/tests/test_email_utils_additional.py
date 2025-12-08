import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import smtplib

from app.utils import email_utils


def test__render_template_replaces_double_and_single_braces():
    tpl = "Hello {{NAME}}, age {AGE}"
    out = email_utils._render_template(tpl, {"NAME": "Alice", "AGE": 30})
    assert "Alice" in out
    assert "30" in out


def test__create_ics_content_sync_contains_expected_fields():
    start = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    content = email_utils._create_ics_content_sync(start, end, "My Summary", "Details here")
    assert "BEGIN:VCALENDAR" in content
    assert "DTSTART:" in content
    assert "DTEND:" in content
    assert "SUMMARY:My Summary" in content
    assert "DESCRIPTION:Details here" in content


def make_cm(on_enter=None, on_login=None, on_send=None):
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


def test__send_interview_email_sync_success(monkeypatch):
    # Patch SMTP to behave normally
    CM = make_cm()
    monkeypatch.setattr(email_utils.smtplib, 'SMTP', CM)

    dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    ok = email_utils._send_interview_email_sync(
        to_email="to@example.com",
        candidate_name="Bob",
        interview_link="https://x",
        interview_token="TKN",
        interview_datetime=dt,
        job_title="Engineer",
    )
    assert ok is True


def test__send_interview_email_sync_failure_on_send(monkeypatch):
    # Patch SMTP to raise on send
    send_exc = smtplib.SMTPException('send failed')
    CM = make_cm(on_send=send_exc)
    monkeypatch.setattr(email_utils.smtplib, 'SMTP', CM)

    dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    ok = email_utils._send_interview_email_sync(
        to_email="to@example.com",
        candidate_name="Bob",
        interview_link="https://x",
        interview_token="TKN",
        interview_datetime=dt,
        job_title="Engineer",
    )
    assert ok is False
