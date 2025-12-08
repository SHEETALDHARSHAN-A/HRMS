import pytest
from datetime import datetime, timezone, timedelta
from app.utils import email_utils


def test_render_template_double_and_single_braces():
    tpl = "Hello {{NAME}}, your code is {CODE}"
    out = email_utils._render_template(tpl, {"NAME": "Alice", "CODE": 1234})
    assert "Alice" in out
    assert "1234" in out


def test_get_preview_email_content_sanitizes_script_and_onclick():
    subject = "Hi {{NAME}}"
    body = '<div onclick="alert(1)">Click</div><script>evil()</script><a href="javascript:doBad()">link</a>'
    rendered_subject, rendered_body = email_utils.get_preview_email_content(subject, body, {"NAME": "Bob"})
    assert "evil()" not in rendered_body
    assert "onclick" not in rendered_body.lower()
    assert "javascript:doBad" not in rendered_body
    assert "Bob" in rendered_subject


def test_create_ics_contains_dtstart_dtend():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    ics = email_utils._create_ics_content_sync(start, end, "Subj", "Desc")
    assert "DTSTART" in ics
    assert "DTEND" in ics


def test_format_role_subject():
    assert email_utils.format_role_subject('SUPER_ADMIN') == 'Super Admin'
    assert email_utils.format_role_subject('ADMIN') == 'Admin'
    assert email_utils.format_role_subject('HR') == 'HR'
    assert email_utils.format_role_subject('SOME_ROLE') == 'SOME_ROLE'
