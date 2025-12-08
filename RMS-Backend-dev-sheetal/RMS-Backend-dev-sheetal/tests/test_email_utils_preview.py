import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.utils import email_utils


def test_get_preview_email_content_unmatched_braces_subject():
    subject = "Hello {{NAME"
    body = "Simple body"
    with pytest.raises(ValueError):
        email_utils.get_preview_email_content(subject, body, {"NAME": "X"})


def test_get_preview_email_content_unmatched_braces_body():
    subject = "Hi {{NAME}}"
    # Use double-brace mismatch so the validator counts unmatched '{{' vs '}}'
    body = "<div>{{UNMATCHED</div>"
    with pytest.raises(ValueError):
        email_utils.get_preview_email_content(subject, body, {"NAME": "X"})


def test_get_preview_email_content_renders_and_sanitizes():
    subject = "Invite for {{NAME}}"
    body = (
        '<div onclick="bad()">Hello {NAME}</div>'
        "<script>alert('x')</script>"
        '<a href="javascript:evil()">link</a>'
    )

    rendered_subject, rendered_body = email_utils.get_preview_email_content(subject, body, {"NAME": "Carol"})

    assert "Carol" in rendered_subject
    assert "Carol" in rendered_body
    # script tag removed
    assert "<script" not in rendered_body
    # inline event handler removed
    assert "onclick" not in rendered_body
    # javascript: href replaced
    assert "javascript:" not in rendered_body
    # Replacement may vary; ensure javascript: removed and an anchor remains with a placeholder
    assert "<a" in rendered_body
    assert "#" in rendered_body


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_none(monkeypatch):
    # ConfigRepository.get_template_by_key returns None
    async def fake_get(db, key):
        return None

    monkeypatch.setattr(email_utils.ConfigRepository, "get_template_by_key", fake_get)

    db = MagicMock()
    rendered_subject, rendered_body = await email_utils._fetch_and_render_saved_template(db, "NONEXISTENT", {"X": "Y"})
    assert rendered_subject is None and rendered_body is None


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_with_record(monkeypatch):
    # Return a fake record that uses single and double brace placeholders
    record = SimpleNamespace(
        subject_template="Hello {NAME}",
        body_template_html="<div>Welcome {{NAME}}<script>bad()</script></div>",
    )

    async def fake_get(db, key):
        return record

    monkeypatch.setattr(email_utils.ConfigRepository, "get_template_by_key", fake_get)

    db = MagicMock()
    rendered_subject, rendered_body = await email_utils._fetch_and_render_saved_template(db, "OTP", {"NAME": "Eve"})

    assert "Eve" in rendered_subject
    assert "Eve" in rendered_body
    # script removed by sanitizer in preview renderer
    assert "<script" not in rendered_body
