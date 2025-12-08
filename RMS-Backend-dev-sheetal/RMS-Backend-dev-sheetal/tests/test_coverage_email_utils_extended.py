import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.utils.email_utils import _fetch_and_render_saved_template
from app.utils import email_utils
from types import SimpleNamespace
import asyncio
import smtplib

@pytest.mark.asyncio
async def test_fetch_saved_template_aliasing(fake_db):
    # Mock repository to simulate template found via alias
    mock_repo_get = AsyncMock()
    # If asked for "INTERVIEW_INVITE", return logic.
    # We simulate the aliasing logic inside _fetch_and_render_saved_template
    # The function internally tries aliases. We just need Repo to return True for one of them.
    
    # Return a fake record for any candidate key that looks like an interview alias
    def side_effect(db, key):
        if key and "INTERVIEW" in key:
            return MagicMock(subject_template="S", body_template_html="B")
        return None

    mock_repo_get.side_effect = side_effect
    
    with patch("app.utils.email_utils.ConfigRepository.get_template_by_key", mock_repo_get):
        # Request with original key
        subj, body = await _fetch_and_render_saved_template(fake_db, "INTERVIEW_INVITE", {})
        
        assert subj == "S"
        assert body == "B"

@pytest.mark.asyncio
async def test_fetch_saved_template_db_error(fake_db):
    with patch("app.utils.email_utils.ConfigRepository.get_template_by_key", side_effect=Exception("DB Error")):
        # If the repository raises during candidate checks the function should
        # swallow per-candidate errors and ultimately return (None, None)
        subj, body = await _fetch_and_render_saved_template(fake_db, "OTP", {})
        assert subj is None and body is None


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_with_saved_template(monkeypatch):
    async def fake_fetch(db, key, context):
        return ("Subject for {{CANDIDATE_NAME}}", "<p>Hello {{CANDIDATE_NAME}}</p>")

    monkeypatch.setattr("app.utils.email_utils._fetch_and_render_saved_template", fake_fetch)
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.utils.email_utils.send_email_async", mock_send)

    from datetime import datetime, timezone

    res = await email_utils.send_interview_invite_email_async(
        to_email="to@example.com",
        candidate_name="Zoe",
        interview_link="https://x",
        interview_token="TKN",
        interview_datetime=datetime(2025,1,1,12,0,tzinfo=timezone.utc),
        job_title="Role",
    )

    assert res is True
    assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_template_required_refuses(monkeypatch):
    async def fake_fetch(db, key, context):
        return (None, None)

    monkeypatch.setattr("app.utils.email_utils._fetch_and_render_saved_template", fake_fetch)
    monkeypatch.setattr("app.utils.email_utils.settings", email_utils.settings)
    monkeypatch.setattr(email_utils.settings, "email_require_templates", True)
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.utils.email_utils.send_email_async", mock_send)

    from datetime import datetime, timezone

    res = await email_utils.send_interview_invite_email_async(
        to_email="to@example.com",
        candidate_name="Zoe",
        interview_link="https://x",
        interview_token="TKN",
        interview_datetime=datetime(2025,1,1,12,0,tzinfo=timezone.utc),
        job_title="Role",
    )

    assert res is False
    assert mock_send.await_count == 0


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_fallbacks_to_custom(monkeypatch):
    async def fake_fetch(db, key, context):
        return (None, None)

    monkeypatch.setattr("app.utils.email_utils._fetch_and_render_saved_template", fake_fetch)
    monkeypatch.setattr("app.utils.email_utils.settings", email_utils.settings)
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.utils.email_utils.send_email_async", mock_send)

    from datetime import datetime, timezone

    res = await email_utils.send_interview_invite_email_async(
        to_email="to@example.com",
        candidate_name="Zed",
        interview_link="https://x",
        interview_token="TKN",
        interview_datetime=datetime(2025,1,1,12,0,tzinfo=timezone.utc),
        job_title="Role",
        custom_subject="Custom {{CANDIDATE_NAME}}",
        custom_body="<p>Hi {CANDIDATE_NAME}</p>",
    )

    assert res is True
    assert mock_send.await_count == 1

def test_render_template_single_and_double_braces_and_non_string_values():
    tpl = "Hello {{NAME}}, your code is {CODE} and count is {{COUNT}}"
    ctx = {"NAME": "Alice", "CODE": 123, "COUNT": 5}
    rendered = email_utils._render_template(tpl, ctx)
    assert "Alice" in rendered
    assert "123" in rendered
    assert "5" in rendered

def test_get_preview_email_content_sanitizes_and_validates_braces():
    subj = "Subject {{A}}"
    body = "<p>Hi {{A}}</p><script>alert('x')</script><a href=\"javascript:evil()\">bad</a><div onload=\"x\">ok</div>"
    ctx = {"A": "B"}
    rsubj, rbody = email_utils.get_preview_email_content(subj, body, ctx)
    assert "B" in rsubj
    assert "alert(" not in rbody
    assert "javascript:" not in rbody
    assert "onload=" not in rbody

    # Unmatched braces should raise
    with pytest.raises(ValueError):
        email_utils.get_preview_email_content("{{A", body, ctx)

def test_create_ics_content_sync_contains_expected_times_and_uid():
    from datetime import datetime, timezone, timedelta
    start = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    ics = email_utils._create_ics_content_sync(start, end, "S", "D")
    assert "DTSTART:20250101T" in ics
    assert "DTEND:20250101T" in ics
    assert "BEGIN:VEVENT" in ics

def test_generate_default_interview_html_contains_context_values():
    ctx = {"CANDIDATE_NAME": "Leo", "ROUND_NAME": "Final", "JOB_TITLE": "Role", "NEXT_ROUND_NAME": "HR", "INTERVIEW_TIME": "time", "ROOM_CODE": "RC", "JOIN_URL": "https://x"}
    html = email_utils._generate_default_interview_html(ctx)
    assert "Leo" in html
    assert "Final" in html
    assert "Role" in html
    assert "RC" in html

def test__send_interview_email_sync_success_and_failure(monkeypatch):
    # Patch smtplib.SMTP to a dummy context manager
    class FakeSMTP:
        def __init__(self, host, port):
            pass
        def starttls(self, context=None):
            return None
        def login(self, user, pw):
            return None
        def send_message(self, msg):
            return None
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    from datetime import datetime, timezone
    ok = email_utils._send_interview_email_sync("t@e.com", "N", "https://x", "T", datetime(2025,1,1,12,0,tzinfo=timezone.utc), "J")
    assert ok is True

    # Simulate SMTP auth error
    class AuthSMTP(FakeSMTP):
        def login(self, user, pw):
            raise smtplib.SMTPAuthenticationError(535, b"Auth failed")
    monkeypatch.setattr(smtplib, "SMTP", AuthSMTP)
    bad = email_utils._send_interview_email_sync("t@e.com", "N", "https://x", "T", datetime(2025,1,1,12,0,tzinfo=timezone.utc), "J")
    assert bad is False

def test__send_email_sync_other_exceptions(monkeypatch):
    class ConnectSMTP:
        def __init__(self, host, port):
            pass
        def starttls(self, context=None):
            raise smtplib.SMTPConnectError(421, b"Cannot connect")
        def login(self, user, pw):
            return None
        def send_message(self, msg):
            return None
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(smtplib, "SMTP", ConnectSMTP)
    from datetime import datetime, timezone
    res = email_utils._send_interview_email_sync("x@e.com", "N", "https://x", "T", datetime(2025,1,1,12,0,tzinfo=timezone.utc), "J")
    assert res is False

    # Test SMTPException in send_message
    class ExSMTP(ConnectSMTP):
        def starttls(self, context=None):
            return None
        def send_message(self, msg):
            raise smtplib.SMTPException("Fail send")
    monkeypatch.setattr(smtplib, "SMTP", ExSMTP)
    res2 = email_utils._send_interview_email_sync("x@e.com", "N", "https://x", "T", datetime(2025,1,1,12,0,tzinfo=timezone.utc), "J")
    assert res2 is False


def test__send_interview_email_sync_generic_exception(monkeypatch):
    class BadSMTP:
        def __init__(self, host, port):
            pass
        def starttls(self, context=None):
            raise Exception("boom")
        def login(self, user, pw):
            return None
        def send_message(self, msg):
            return None
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(smtplib, "SMTP", BadSMTP)
    from datetime import datetime, timezone
    res = email_utils._send_interview_email_sync("x@e.com", "N", "https://x", "T", datetime(2025,1,1,12,0,tzinfo=timezone.utc), "J")
    assert res is False


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_exception_returns_false(monkeypatch):
    # Patch the async send to raise so the wrapper returns False
    async def raise_exc(*a, **kw):
        raise Exception("boom")
    monkeypatch.setattr(email_utils, "send_email_async", raise_exc)
    from datetime import datetime, timezone
    res = await email_utils.send_interview_invite_email_async("a@b.com", "N", "https://x", "T", datetime(2025,1,1,9,0,tzinfo=timezone.utc), "J")
    assert res is False


@pytest.mark.asyncio
async def test_send_email_async_catches_exceptions(monkeypatch):
    monkeypatch.setattr(email_utils, "_send_email_sync", lambda s, r, h: (_ for _ in ()).throw(Exception("boom")))
    res = await email_utils.send_email_async("S", "t@e.com", "<p>html</p>")
    assert res is False


@pytest.mark.asyncio
async def test_send_admin_removal_email_default_display(monkeypatch):
    # Capture html content when admin_name None -> default 'Valued User'
    async def capture(subject, recipient, html):
        capture.called = True
        capture.html = html
        return True
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    monkeypatch.setattr(email_utils, "send_email_async", capture)
    await email_utils.send_admin_removal_email("t@e.com", None)
    assert getattr(capture, 'called', False) is True
    assert "Valued User" in capture.html


@pytest.mark.asyncio
async def test_send_admin_role_change_email_send_failure_returns_false(monkeypatch):
    # If underlying send raises, function should return False
    async def raise_send(*a, **kw):
        raise Exception("boom")
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils, "send_email_async", raise_send)
    res = await email_utils.send_admin_role_change_email("t@e.com", "A", "ADMIN", "SUPER_ADMIN")
    assert res is False


@pytest.mark.asyncio
async def test_send_admin_role_change_invalid_roles_promoted_flag(monkeypatch):
    captured = {}
    async def capture(subject, recipient, html):
        captured['subject'] = subject
        captured['html'] = html
        return True
    monkeypatch.setattr(email_utils, "send_email_async", capture)
    # invalid roles (not in roles_order) will fall back to promoted = new_role != old_role
    res = await email_utils.send_admin_role_change_email("t@e.com", "Alice", "X", "Y", performed_by="Bob")
    assert res is True
    assert "Promoted" in captured['subject'] or "Demoted" in captured['subject'] or "Updated" in captured['subject']


@pytest.mark.asyncio
async def test_send_email_change_transfer_notification_approval_block(monkeypatch):
    # Ensure approval_link branch produces html with link
    captured = {}
    async def capture(subject, recipient, html):
        captured['html'] = html
        return True
    monkeypatch.setattr(email_utils, "send_email_async", capture)
    res = await email_utils.send_email_change_transfer_notification("old@e.com", "Admin", "new@e.com", approval_link="https://approve")
    assert res is True
    assert "https://approve" in captured['html']


@pytest.mark.asyncio
async def test_send_otp_for_email_update_html_contains_otp(monkeypatch):
    captured = {}
    async def capture(subject, recipient, html):
        captured['html'] = html
        return True
    monkeypatch.setattr(email_utils, "send_email_async", capture)
    res = await email_utils.send_otp_for_email_update("a@b.com", "Admin", "1111")
    assert res is True
    assert "1111" in captured['html']


@pytest.mark.asyncio
async def test_send_admin_removal_email_shows_admin_name(monkeypatch):
    captured = {}
    async def capture(subject, recipient, html):
        captured['html'] = html
        return True
    monkeypatch.setattr(email_utils, "send_email_async", capture)
    res = await email_utils.send_admin_removal_email("t@e.com", "AdminName")
    assert res is True
    assert "AdminName" in captured['html']


@pytest.mark.asyncio
async def test_send_email_change_transfer_notification_no_approval_block(monkeypatch):
    captured = {}
    async def capture(subject, recipient, html):
        captured['html'] = html
        return True
    monkeypatch.setattr(email_utils, "send_email_async", capture)
    res = await email_utils.send_email_change_transfer_notification("old@e.com", "Admin", "new@e.com", approval_link=None)
    assert res is True
    assert "Approve Email Transfer" not in captured['html']


@pytest.mark.asyncio
async def test_send_admin_invite_expires_formatting_and_template_error(monkeypatch):
    # Force expire formatting exception by passing an object with tzinfo property that raises
    class BadDate:
        @property
        def tzinfo(self):
            raise Exception("bad tzinfo")
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    from datetime import datetime, timezone
    res = await email_utils.send_admin_invite_email("t@e.com", "Admin", "https://x", BadDate())
    assert res is True


@pytest.mark.asyncio
async def test_fetch_and_render_saved_template_raises_on_preview_error(fake_db):
    # When stored template has unmatched braces, get_preview_email_content will raise
    record = SimpleNamespace(subject_template="Hello {{NAME", body_template_html="<p>Hi {{NAME}}</p>")
    async def get(db, key):
        return record
    with patch("app.utils.email_utils.ConfigRepository.get_template_by_key", AsyncMock(side_effect=get)):
        with pytest.raises(ValueError):
            await email_utils._fetch_and_render_saved_template(fake_db, "INTERVIEW_INVITE", {"NAME": "X"})


@pytest.mark.asyncio
async def test_send_email_async_and__send_email_sync_paths(monkeypatch):
    # Patch _send_email_sync to return True/False through asyncio.to_thread
    monkeypatch.setattr(email_utils, "_send_email_sync", lambda s, r, h: True)
    res = await email_utils.send_email_async("S", "t@e.com", "<p>html</p>")
    assert res is True
    # Make sync raise
    def raise_err(s, r, h):
        raise Exception("boom")
    monkeypatch.setattr(email_utils, "_send_email_sync", raise_err)
    res2 = await email_utils.send_email_async("S", "t@e.com", "<p>html</p>")
    assert res2 is False

@pytest.mark.asyncio
async def test_send_otp_email_and_admin_paths(monkeypatch):
    # OTP: saved template -> send_email_async should be called
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=("S", "<p>OTP</p>")))
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    res = await email_utils.send_otp_email("t@e.com", "1111", "S")
    assert res is True

    # OTP: no template but settings.email_require_templates True -> return False
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", True)
    res2 = await email_utils.send_otp_email("t@e.com", "1111", "S")
    assert res2 is False

    # Admin removal fallbacks
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    ok = await email_utils.send_admin_removal_email("t@e.com", "Admin")
    assert ok is True

@pytest.mark.asyncio
async def test_template_getters_and_format_role_subject():
    # Call default getters to ensure they return strings
    assert isinstance(email_utils.get_default_interview_template_content(), tuple)
    assert isinstance(email_utils.get_default_admin_invite_template_content(), tuple)
    assert isinstance(email_utils.get_default_admin_role_update_template_content(), tuple)
    assert isinstance(email_utils.get_default_admin_delete_template_content(), tuple)
    assert isinstance(email_utils.get_default_otp_template_content(), tuple)
    assert isinstance(email_utils.get_default_email_update_verification_template_content(), tuple)
    assert isinstance(email_utils.get_default_email_change_transfer_notification_template_content(), tuple)
    assert isinstance(email_utils.get_default_name_update_verification_template_content(), tuple)
    assert isinstance(email_utils.get_default_name_update_success_template_content(), tuple)
    assert isinstance(email_utils.get_default_phone_update_verification_template_content(), tuple)
    assert isinstance(email_utils.get_default_otp_for_email_update_template_content(), tuple)
    # format_role_subject
    assert email_utils.format_role_subject('SUPER_ADMIN') == 'Super Admin'
    assert email_utils.format_role_subject('ADMIN') == 'Admin'
    assert email_utils.format_role_subject('HR') == 'HR'
    assert email_utils.format_role_subject('UNKNOWN') == 'UNKNOWN'


    


@pytest.mark.asyncio
async def test_fetch_saved_template_single_brace_normalizes_and_renders(fake_db):
    # Return a record object with single brace placeholders
    record = SimpleNamespace(subject_template="Hello {CANDIDATE_NAME}", body_template_html="<p>Hi {CANDIDATE_NAME}</p>")
    async def fake_get(db, key):
        return record
    with patch("app.utils.email_utils.ConfigRepository.get_template_by_key", AsyncMock(side_effect=fake_get)):
        subj, body = await email_utils._fetch_and_render_saved_template(fake_db, "INTERVIEW_INVITE", {"CANDIDATE_NAME": "Jo"})
        assert "Jo" in subj
        assert "Jo" in body


@pytest.mark.asyncio
async def test_send_interview_invite_email_async_fallbacks_to_default_inline(monkeypatch):
    # No saved template; settings allow fallback to inline default
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    # Patch default template getter to known values
    monkeypatch.setattr(email_utils, "get_default_interview_template_content", lambda: ("Default {{JOB_TITLE}}", "<p>{{CANDIDATE_NAME}}</p>"))
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", sent)
    from datetime import datetime, timezone
    res = await email_utils.send_interview_invite_email_async(
        to_email="a@b.com",
        candidate_name="Z",
        interview_link="https://x",
        interview_token="T",
        interview_datetime=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        job_title="J",
    )
    assert res is True
    assert sent.await_count == 1


@pytest.mark.asyncio
async def test_admin_related_email_functions_cover_fallbacks(monkeypatch):
    # Test admin_invite fallback no template
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    from datetime import datetime, timezone
    ok = await email_utils.send_admin_invite_email("t@e.com", "Admin", "https://x", datetime(2025,1,1,12,0,tzinfo=timezone.utc))
    assert ok is True

    # Admin role change promoted and demoted
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    ok1 = await email_utils.send_admin_role_change_email("t@e.com", "A", "HR", "ADMIN")
    ok2 = await email_utils.send_admin_role_change_email("t@e.com", "A", "ADMIN", "HR")
    assert ok1 is True
    assert ok2 is True


@pytest.mark.asyncio
async def test_send_email_update_verification_and_change_transfer_and_name_phone(monkeypatch):
    # Test update verification with api_info adding endpoint
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    ok = await email_utils.send_email_update_verification_link("n@e.com", "Admin", "https://v", "old@e.com", api_info={"endpoint":"/verify/123"})
    assert ok is True

    ok2 = await email_utils.send_email_change_transfer_notification("old@e.com", "Admin", "new@e.com", approval_link="https://a")
    assert ok2 is True

    ok3 = await email_utils.send_name_update_verification_link("t@e.com", "Old Name", "New Name", "https://v")
    assert ok3 is True
    ok4 = await email_utils.send_name_update_success_notification("t@e.com", "New Name")
    assert ok4 is True
    ok5 = await email_utils.send_phone_update_verification_link("t@e.com", "Admin", "9876", "0123", "https://v")
    assert ok5 is True
    ok6 = await email_utils.send_otp_for_email_update("t@e.com", "Admin", "1111")
    assert ok6 is True


@pytest.mark.asyncio
async def test_all_send_functions_saved_template_present(monkeypatch):
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=("Sub", "<p>B</p>")))
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", sent)
    from datetime import datetime, timezone

    tasks = [
        (email_utils.send_interview_invite_email_async, ["a@b.com", "N", "https://x", "T", datetime(2025,1,1,9,0,tzinfo=timezone.utc), "J"], {}),
        (email_utils.send_otp_email, ["a@b.com", "1111", "S"], {}),
        (email_utils.send_admin_removal_email, ["a@b.com", "Admin"], {}),
        (email_utils.send_admin_invite_email, ["a@b.com", "Admin", "https://x", datetime(2025,1,1,9,0,tzinfo=timezone.utc)], {}),
        (email_utils.send_admin_role_change_email, ["a@b.com", "Admin", "HR", "ADMIN"], {}),
        (email_utils.send_email_update_verification_link, ["a@b.com", "Admin", "https://v", "old@e.com"], {}),
        (email_utils.send_email_change_transfer_notification, ["old@e.com", "Admin", "new@e.com"], {}),
        (email_utils.send_name_update_verification_link, ["a@b.com", "Old", "New", "https://v"], {}),
        (email_utils.send_name_update_success_notification, ["a@b.com", "New"], {}),
        (email_utils.send_phone_update_verification_link, ["a@b.com", "Admin", "111", "222", "https://v"], {}),
        (email_utils.send_otp_for_email_update, ["a@b.com", "Admin", "1111"], {}),
    ]

    for fn, args, kwargs in tasks:
        sent.reset_mock()
        res = await fn(*args, **kwargs)
        assert res is True
        assert sent.await_count == 1


@pytest.mark.asyncio
async def test_all_send_functions_template_required_refuse(monkeypatch):
    # If email_require_templates True and no saved template - should refuse (return False)
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", True)
    monkeypatch.setattr(email_utils, "send_email_async", AsyncMock(return_value=True))
    from datetime import datetime, timezone

    tasks = [
        (email_utils.send_interview_invite_email_async, ["a@b.com", "N", "https://x", "T", datetime(2025,1,1,9,0,tzinfo=timezone.utc), "J"], {}),
        (email_utils.send_otp_email, ["a@b.com", "1111", "S"], {}),
        (email_utils.send_admin_removal_email, ["a@b.com", "Admin"], {}),
        (email_utils.send_admin_invite_email, ["a@b.com", "Admin", "https://x", datetime(2025,1,1,9,0,tzinfo=timezone.utc)], {}),
        (email_utils.send_admin_role_change_email, ["a@b.com", "Admin", "HR", "ADMIN"], {}),
        (email_utils.send_email_update_verification_link, ["a@b.com", "Admin", "https://v", "old@e.com"], {}),
        (email_utils.send_email_change_transfer_notification, ["old@e.com", "Admin", "new@e.com"], {}),
        (email_utils.send_name_update_verification_link, ["a@b.com", "Old", "New", "https://v"], {}),
        (email_utils.send_name_update_success_notification, ["a@b.com", "New"], {}),
        (email_utils.send_phone_update_verification_link, ["a@b.com", "Admin", "111", "222", "https://v"], {}),
        (email_utils.send_otp_for_email_update, ["a@b.com", "Admin", "1111"], {}),
    ]

    for fn, args, kwargs in tasks:
        res = await fn(*args, **kwargs)
        assert res is False


@pytest.mark.asyncio
async def test_all_send_functions_template_missing_fallbacks(monkeypatch):
    # With email_require_templates False, missing template should fallback to inline default and send
    monkeypatch.setattr(email_utils, "_fetch_and_render_saved_template", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(email_utils.settings, "email_require_templates", False)
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(email_utils, "send_email_async", sent)
    from datetime import datetime, timezone

    tasks = [
        (email_utils.send_interview_invite_email_async, ["a@b.com", "N", "https://x", "T", datetime(2025,1,1,9,0,tzinfo=timezone.utc), "J"], {}),
        (email_utils.send_otp_email, ["a@b.com", "1111", "S"], {}),
        (email_utils.send_admin_removal_email, ["a@b.com", "Admin"], {}),
        (email_utils.send_admin_invite_email, ["a@b.com", "Admin", "https://x", datetime(2025,1,1,9,0,tzinfo=timezone.utc)], {}),
        (email_utils.send_admin_role_change_email, ["a@b.com", "Admin", "HR", "ADMIN"], {}),
        (email_utils.send_email_update_verification_link, ["a@b.com", "Admin", "https://v", "old@e.com"], {}),
        (email_utils.send_email_change_transfer_notification, ["old@e.com", "Admin", "new@e.com"], {}),
        (email_utils.send_name_update_verification_link, ["a@b.com", "Old", "New", "https://v"], {}),
        (email_utils.send_name_update_success_notification, ["a@b.com", "New"], {}),
        (email_utils.send_phone_update_verification_link, ["a@b.com", "Admin", "111", "222", "https://v"], {}),
        (email_utils.send_otp_for_email_update, ["a@b.com", "Admin", "1111"], {}),
    ]

    for fn, args, kwargs in tasks:
        sent.reset_mock()
        res = await fn(*args, **kwargs)
        assert res is True
        assert sent.await_count == 1


    


    


    


    


    

