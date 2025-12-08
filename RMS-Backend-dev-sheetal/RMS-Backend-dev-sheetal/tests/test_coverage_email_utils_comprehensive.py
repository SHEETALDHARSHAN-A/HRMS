"""
Comprehensive tests for email_utils.py
Targets critical exception paths, template fallbacks, and error handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock as AM
from types import SimpleNamespace
from datetime import datetime, timezone
import smtplib

# =================================================================================================
# email_utils.py Tests (88%, 71 lines missing)
# Key areas: Template fallbacks, SMTP errors, validation, sanitization
# =================================================================================================

def test_render_template_basic():
    """Test _render_template with double and single braces"""
    from app.utils.email_utils import _render_template
    
    template = "Hello {{NAME}}, your code is {CODE}"
    context = {"NAME": "John", "CODE": "12345"}
    
    result = _render_template(template, context)
    
    assert "John" in result
    assert "12345" in result


@pytest.mark.asyncio
async def test_fetch_template_no_db():
    """Test _fetch_and_render_saved_template with no DB - covers line 70"""
    from app.utils.email_utils import _fetch_and_render_saved_template
    
    result = await _fetch_and_render_saved_template(None, "TEST_KEY", {})
    
    assert result == (None, None)


@pytest.mark.asyncio
async def test_fetch_template_exception_handling():
    """Test _fetch_and_render_saved_template exception in repo call - covers lines 111-112"""
    from app.utils.email_utils import _fetch_and_render_saved_template
    
    mock_db = AsyncMock()
    
    with patch('app.utils.email_utils.ConfigRepository.get_template_by_key') as mock_get:
        mock_get.side_effect = Exception("DB error")
        
        result = await _fetch_and_render_saved_template(mock_db, "TEST", {})
        
        # Should return None, None when no template found
        assert result == (None, None)


@pytest.mark.asyncio
async def test_fetch_template_no_record():
    """Test _fetch_and_render_saved_template when no record found - covers line 118"""
    from app.utils.email_utils import _fetch_and_render_saved_template
    
    mock_db = AsyncMock()
    
    with patch('app.utils.email_utils.ConfigRepository.get_template_by_key') as mock_get:
        mock_get.return_value = None  # No record
        
        result = await _fetch_and_render_saved_template(mock_db, "MISSING_KEY", {})
        
        assert result == (None, None)


@pytest.mark.asyncio
async def test_fetch_template_regex_error_fallback():
    """Test template regex normalization error fallback - covers lines 129-131"""
    from app.utils.email_utils import _fetch_and_render_saved_template
    
    mock_db = AsyncMock()
    mock_record = SimpleNamespace(
        subject_template="Test {SUBJECT}",
        body_template_html="Body {CONTENT}"
    )
    
    with patch('app.utils.email_utils.ConfigRepository.get_template_by_key') as mock_get:
        with patch('app.utils.email_utils.re.sub') as mock_sub:
            mock_get.return_value = mock_record
            mock_sub.side_effect = Exception("Regex error")
            
            with patch('app.utils.email_utils.get_preview_email_content') as mock_preview:
                mock_preview.return_value = ("Subject", "Body")
                
                result = await _fetch_and_render_saved_template(mock_db, "TEST", {})
                
                # Should still render with fallback
                assert result is not None


def test_validate_braces_unmatched():
    """Test brace validation with unmatched braces - covers lines 691-692"""
    from app.utils.email_utils import get_preview_email_content
    
    template = "Hello {{NAME"  # Unmatched braces
    
    with pytest.raises(ValueError) as exc_info:
        get_preview_email_content(template, "Body", {})
    
    assert "unmatched braces" in str(exc_info.value).lower()


def test_validate_braces_none_input():
    """Test brace validation with None input - covers lines 687-688"""
    from app.utils.email_utils import get_preview_email_content
    
    # Should not raise when subject is None
    result = get_preview_email_content("", None, {})
    assert result is not None


def test_sanitize_html_removes_scripts():
    """Test HTML sanitization removes scripts - covers line 706"""
    from app.utils.email_utils import get_preview_email_content
    
    malicious_html = "<p>Hello</p><script>alert('xss')</script>"
    
    _, sanitized = get_preview_email_content("Subject", malicious_html, {})
    
    assert "<script>" not in sanitized
    assert "alert" not in sanitized


def test_sanitize_html_removes_event_handlers():
    """Test HTML sanitization removes event handlers - covers lines 708-709"""
    from app.utils.email_utils import get_preview_email_content
    
    html_with_events = '<div onclick="alert(1)">Click</div>'
    
    _, sanitized = get_preview_email_content("Subject", html_with_events, {})
    
    assert "onclick" not in sanitized


def test_sanitize_html_removes_javascript_urls():
    """Test HTML sanitization removes javascript: URLs - covers lines 711-712"""
    from app.utils.email_utils import get_preview_email_content
    
    html = '<a href="javascript:void(0)">Link</a>'
    
    _, sanitized = get_preview_email_content("Subject", html, {})
    
    assert "javascript:" not in sanitized


def test_send_email_sync_smtp_auth_error():
    """Test _send_email_sync with SMTP auth error - covers lines 741-743"""
    from app.utils.email_utils import _send_email_sync
    
    with patch('app.utils.email_utils.smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")
        
        result = _send_email_sync("Subject", "test@example.com", "<p>Body</p>")
        
        assert result is False


def test_send_email_sync_smtp_connect_error():
    """Test _send_email_sync with SMTP connect error - covers lines 744-746"""
    from app.utils.email_utils import _send_email_sync
    
    with patch('app.utils.email_utils.smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Cannot connect")
        
        result = _send_email_sync("Subject", "test@example.com", "<p>Body</p>")
        
        assert result is False


def test_send_email_sync_smtp_exception():
    """Test _send_email_sync with general SMTP exception - covers lines 747-749"""
    from app.utils.email_utils import _send_email_sync
    
    with patch('app.utils.email_utils.smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.send_message.side_effect = smtplib.SMTPException("SMTP error")
        
        result = _send_email_sync("Subject", "test@example.com", "<p>Body</p>")
        
        assert result is False


def test_send_email_sync_unexpected_error():
    """Test _send_email_sync with unexpected error - covers lines 750-752"""
    from app.utils.email_utils import _send_email_sync
    
    with patch('app.utils.email_utils.smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = RuntimeError("Unexpected")
        
        result = _send_email_sync("Subject", "test@example.com", "<p>Body</p>")
        
        assert result is False


@pytest.mark.asyncio
async def test_send_email_async_exception_wrapper():
    """Test send_email_async exception handling - covers lines 777-779"""
    from app.utils.email_utils import send_email_async
    
    with patch('app.utils.email_utils.asyncio.to_thread') as mock_thread:
        mock_thread.side_effect = Exception("Thread error")
        
        result = await send_email_async("Subject", "test@example.com", "<p>Body</p>")
        
        assert result is False


@pytest.mark.asyncio
async def test_send_interview_email_with_custom_template():
    """Test send_interview_invite_email_async with custom templates - covers lines 352-358"""
    from app.utils.email_utils import send_interview_invite_email_async
    
    interview_dt = datetime.now(timezone.utc)
    
    with patch('app.utils.email_utils._fetch_and_render_saved_template') as mock_fetch:
        with patch('app.utils.email_utils.send_email_async') as mock_send:
            mock_fetch.return_value = (None, None)  # No saved template
            mock_send.return_value = True
            
            # Provide custom subject/body
            result = await send_interview_invite_email_async(
                to_email="candidate@test.com",
                candidate_name="John Doe",
                interview_link="https://meet.com/abc",
                interview_token="ABC123",
                interview_datetime=interview_dt,
                job_title="Engineer",
                custom_subject="Custom Subject",
                custom_body="Custom Body {{CANDIDATE_NAME}}",
                db=None
            )
            
            assert mock_send.called


@pytest.mark.asyncio
async def test_send_interview_email_template_required_mode():
    """Test send_interview_invite when templates required but missing - covers lines 347-349"""
    from app.utils.email_utils import send_interview_invite_email_async
    
    interview_dt = datetime.now(timezone.utc)
    
    with patch('app.utils.email_utils._fetch_and_render_saved_template') as mock_fetch:
        with patch('app.utils.email_utils.settings') as mock_settings:
            mock_fetch.return_value = (None, None)  # No template
            mock_settings.email_require_templates = True  # Template required
            
            result = await send_interview_invite_email_async(
                to_email="test@example.com",
                candidate_name="Test",
                interview_link="https://link.com",
                interview_token="TOKEN",
                interview_datetime=interview_dt,
                job_title="Job",
                db=None
            )
            
            # Should refuse to send
            assert result is False


@pytest.mark.asyncio
async def test_send_interview_email_error_fetching_template():
    """Test send_interview_invite when template fetch raises error - covers lines 359-361"""
    from app.utils.email_utils import send_interview_invite_email_async
    
    interview_dt = datetime.now(timezone.utc)
    
    with patch('app.utils.email_utils._fetch_and_render_saved_template') as mock_fetch:
        mock_fetch.side_effect = Exception("DB connection lost")
        
        result = await send_interview_invite_email_async(
            to_email="test@example.com",
            candidate_name="Test",
            interview_link="https://link.com",
            interview_token="TOKEN",
            interview_datetime=interview_dt,
            job_title="Job",
            db=AsyncMock()
        )
        
        assert result is False


@pytest.mark.asyncio
async def test_send_otp_email_template_fallback():
    """Test send_otp_email fallback to default template - covers OTP template paths"""
    from app.utils.email_utils import send_otp_email
    
    with patch('app.utils.email_utils._fetch_and_render_saved_template') as mock_fetch:
        with patch('app.utils.email_utils.send_email_async') as mock_send:
            mock_fetch.return_value = (None, None)  # No saved template
            mock_send.return_value = True
            
            result = await send_otp_email("test@example.com", "123456", "OTP Subject", db=None)
            
            assert mock_send.called


@pytest.mark.asyncio
async def test_send_admin_invite_email_with_db():
    """Test send_admin_invite_email with DB session"""
    from app.utils.email_utils import send_admin_invite_email
    
    mock_db = AsyncMock()
    
    with patch('app.utils.email_utils._fetch_and_render_saved_template') as mock_fetch:
        with patch('app.utils.email_utils.send_email_async') as mock_send:
            mock_fetch.return_value = ("Subject", "Body")
            mock_send.return_value = True
            
            result = await send_admin_invite_email(
                "admin@test.com",
                "Admin Name",
                "https://invite.link",
                "24 hours",
                db=mock_db
            )
            
            assert result is True
