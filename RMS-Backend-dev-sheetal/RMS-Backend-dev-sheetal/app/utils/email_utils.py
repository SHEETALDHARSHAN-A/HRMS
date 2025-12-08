import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.app_config import AppConfig
from app.db.repository.config_repository import ConfigRepository
from sqlalchemy.ext.asyncio import AsyncSession
import re
from typing import Optional, Dict, Any # Added Dict, Any
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta, timezone
import uuid
import logging
import asyncio
import smtplib

from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta, timezone

from app.config.app_config import AppConfig

logger = logging.getLogger(__name__)

settings = AppConfig()

SMTP_SERVER = settings.smtp_server
SMTP_PORT = settings.smtp_port
SMTP_USERNAME = settings.smtp_username
SMTP_PASSWORD = settings.smtp_password
SENDER_EMAIL = settings.smtp_username

# Global assumption: server is in IST for display preference (UTC +5:30)
DISPLAY_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


# NEW HELPER FUNCTION: Template Renderer
def _render_template(template_string: str, context: Dict[str, str | Any]) -> str:
    """
    Renders a template string by replacing {{PLACEHOLDER}} tags with context values.
    Uses basic string replacement. Placeholders are expected in format: {{KEY}}.
    """
    rendered_string = template_string
    # Iterate through dynamic data and replace the placeholders.
    # Support both double-brace {{KEY}} and legacy single-brace {KEY} placeholders
    # so templates coming from different sources (frontend/editor or legacy
    # stored templates) are rendered correctly.
    for key, value in context.items():
        # placeholder using double braces, e.g. {{OTP_CODE}}
        placeholder_double = f"{{{{{key}}}}}"
        # legacy single-brace placeholder, e.g. {OTP_CODE}
        placeholder_single = f"{{{key}}}"
        # Ensure value is converted to string for safe replacement
        rendered_string = rendered_string.replace(placeholder_double, str(value))
        rendered_string = rendered_string.replace(placeholder_single, str(value))
    return rendered_string
# END NEW HELPER FUNCTION


async def _fetch_and_render_saved_template(db: AsyncSession, template_key: str, context: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Attempts to fetch a saved template by key from the DB and render it with the provided context.
    Returns (rendered_subject, rendered_body) or (None, None) if no saved template exists.
    Any rendering errors are propagated to the caller to allow fallback handling.
    """
    if not db:
        return None, None

    try:
        # Try multiple candidate keys to be tolerant of frontend/backend naming differences
        # Examples: ADMIN_ROLE_CHANGE vs admin_role_change vs AdminRoleChange
        candidates = []
        if template_key:
            candidates.extend([
                template_key,
                template_key.upper(),
                template_key.lower(),
                template_key.replace('-', '_'),
                template_key.replace(' ', '_'),
                template_key.replace('-', '_').upper(),
            ])

        # Add a few sensible aliases for common admin/interview templates
        alias_map = {
            'ADMIN_ROLE_CHANGE': ['ADMIN_ROLE_UPDATED', 'ADMIN_PROMOTION', 'ADMIN_DEMOTION', 'ADMIN_ROLE'],
            'ADMIN_INVITE': ['ADMIN_INVITATION', 'ADMIN_ONBOARD', 'ADMIN_INVITE_LINK'],
            'INTERVIEW_INVITE': ['INTERVIEW_INVITATION', 'CANDIDATE_INTERVIEW_SCHEDULED', 'INTERVIEW_INVITE_LINK'],
            'OTP': ['ONE_TIME_PASSWORD', 'EMAIL_OTP'],
        }
        # If template_key matches an alias map key (case-insensitive), extend candidates
        for k, aliases in alias_map.items():
            if template_key and (template_key.upper() == k or template_key.lower() == k.lower()):
                candidates.extend(aliases)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                deduped.append(c)

        record = None
        matched_key = None
        for candidate in deduped:
            try:
                record = await ConfigRepository.get_template_by_key(db, candidate)
            except Exception:
                record = None
            if record:
                matched_key = candidate
                break

        if not record:
            return None, None

        # Normalize common single-brace placeholders like {ADMIN_NAME} -> {{ADMIN_NAME}}
        subject_template = record.subject_template or ""
        body_template = record.body_template_html or ""

        # Replace occurrences of {KEY} with {{KEY}} unless already using double braces.
        # Only match all-caps/underscore keys to avoid touching normal text with braces.
        try:
            subject_template = re.sub(r'(?<!\{)\{([A-Z0-9_]+)\}(?!\})', r'{{\1}}', subject_template)
            body_template = re.sub(r'(?<!\{)\{([A-Z0-9_]+)\}(?!\})', r'{{\1}}', body_template)
        except Exception:
            # If regex fails for some reason, fall back to the raw templates.
            pass

        logger.info(f"Using saved email template for key='{matched_key}' (requested='{template_key}')")

        # Use local preview renderer which validates braces and sanitizes HTML
        rendered_subject, rendered_body = get_preview_email_content(
            subject_template, body_template, context
        )
        return rendered_subject, rendered_body
    except Exception:
        # Let caller decide what to do on errors (fallback to inline template)
        raise


def _create_ics_content_sync(start_time: datetime, end_time: datetime, summary: str, description: str) -> str:
    """Generates ICS file content as a string."""
    dtstamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dtstart = start_time.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dtend = end_time.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    return f"""
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//RMS Interview Management//Interview Invitation//EN
BEGIN:VEVENT
UID:{uuid.uuid4()}
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
END:VEVENT
END:VCALENDAR
    """.strip()



def _generate_default_interview_html(context: dict) -> str:
    """
    Generates the hardcoded default HTML body, replacing placeholders using the context.
    This ensures the default content is always rendered correctly before being sent 
    or shown in the preview if no custom template is saved.
    """
    # Extract context values used in the default template structure
    candidate_name = context.get("CANDIDATE_NAME", "Candidate")
    round_name = context.get("ROUND_NAME", "Interview")
    job_title = context.get("JOB_TITLE", "Job Position")
    next_round_name = context.get("NEXT_ROUND_NAME", "Final Round")
    display_time = context.get("INTERVIEW_TIME", "TBD")
    interview_token = context.get("ROOM_CODE", "N/A")
    interview_link = context.get("JOIN_URL", "#")

    # The HTML structure remains hardcoded, but values are dynamically inserted.
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h2 style="color: #0b2447; text-align: center;">Interview Invitation</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>

            <p>You have been shortlisted for the {round_name} round for the {job_title}</p>
            <p>The next round after this will be: <strong>{next_round_name}</strong></p>

            <p><strong>Scheduled Date & Time:</strong><br>{display_time}</p>
            <p><strong>Room ID:</strong> {interview_token}</p>

            <p>The interview link below will be active near the scheduled time. Use the Room ID to join.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{interview_link}" style="background-color: #0b2447; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Join Interview</a>
            </div>

            <p style="margin-top: 40px;">
                Regards,<br>
                <strong>The RMS Team</strong>
            </p>
        </div>
    </body>
    </html>
    """
    return html_body


# MODIFIED FUNCTION: _send_interview_email_sync
def _send_interview_email_sync(to_email: str, candidate_name: str, interview_link: str, interview_token: str, interview_datetime: datetime, job_title: str, round_name: str = "Interview round", next_round_name: str = "Final Round", custom_subject: Optional[str] = None, custom_body: Optional[str] = None ) -> bool:
    """
    Synchronous logic to send the HTML email with ICS calendar invite attachment,
    now supporting dynamic templates.
    """
    # FIX: Convert UTC time to a user-friendly display time (e.g., IST) 
    display_datetime_local = interview_datetime.astimezone(DISPLAY_TIMEZONE)
    display_time = f"{display_datetime_local.strftime('%d-%m-%Y %I:%M %p')}"
    
    # 1. DEFINE ALL AVAILABLE DYNAMIC DATA (CONTEXT)
    context = {
        "CANDIDATE_NAME": candidate_name,
        "JOIN_URL": interview_link,
        "ROOM_CODE": interview_token,
        # Display time is the rendered/formatted time
        "INTERVIEW_TIME": display_time, 
        "JOB_TITLE": job_title,
        "ROUND_NAME": round_name,
        "NEXT_ROUND_NAME": next_round_name,
    }

    if custom_subject and custom_body:
        # 2. RENDER THE CUSTOM TEMPLATES
        subject = _render_template(custom_subject, context)
        html_body = _render_template(custom_body, context)
    else:
        # 3. FALLBACK TO EXISTING HARDCODED TEMPLATE (Original logic)
        subject = f"Interview Invitation - {job_title} at Smart HR Agent"

        # ------------------ HTML Body ------------------
        html_body = _generate_default_interview_html(context)

    # Build the email
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    # Create and attach the ICS file
    start_time = interview_datetime
    end_time = start_time + timedelta(hours=1)
    
    # Use templating for ICS description for consistency
    ics_description_template = "Interview for the position. Room code: {{ROOM_CODE}}. Link: {{JOIN_URL}}"
    ics_description = _render_template(ics_description_template, context)

    ics_content = _create_ics_content_sync(
        start_time,
        end_time,
        subject, # Use the dynamic/custom subject
        ics_description 
    )
    # Use method=REQUEST for event (Critical for Outlook/Gmail to process the event correctly)
    ics_part = MIMEApplication(ics_content.encode('utf-8'), 'calendar; method=REQUEST') 
    ics_part.add_header('Content-Disposition', 'attachment; filename="interview.ics"')
    msg.attach(ics_part)

    # Send via SMTP (Reusing existing logic for SMTP connection from _send_email_sync)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        return False

async def send_interview_invite_email_async(
    to_email: str,
    candidate_name: str,
    interview_link: str,
    interview_token: str,
    interview_datetime: datetime,
    job_title: str,
    round_name: str = "Interview round",
    next_round_name: str = "Final Round",
    custom_subject: Optional[str] = None,
    custom_body: Optional[str] = None,
    db: AsyncSession | None = None,
) -> bool:
    """Async wrapper for the synchronous email sender.

    This wrapper will attempt to use a saved template (if present) before
    falling back to client-provided custom_subject/custom_body or the
    built-in default template.
    """
    try:
        # Build rendering context matching template placeholders
        display_datetime_local = interview_datetime.astimezone(DISPLAY_TIMEZONE)
        display_time = f"{display_datetime_local.strftime('%d-%m-%Y %I:%M %p')}"
        context = {
            "CANDIDATE_NAME": candidate_name,
            "JOIN_URL": interview_link,
            "ROOM_CODE": interview_token,
            "INTERVIEW_TIME": display_time,
            "JOB_TITLE": job_title,
            "ROUND_NAME": round_name,
            "NEXT_ROUND_NAME": next_round_name,
        }

        rendered_subject = None
        rendered_body = None

        # Try to fetch a saved template if a DB session is available (or create one)
        try:
            if db is None:
                # Lazily create a short-lived DB session
                from app.db.connection_manager import AsyncSessionLocal
                async with AsyncSessionLocal() as temp_db:
                    rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "INTERVIEW_INVITE", context)
            else:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "INTERVIEW_INVITE", context)
        except Exception:
            # Swallow - we'll fallback to provided/custom/default templates
            rendered_subject, rendered_body = None, None

        # Require saved template for interview invites. Attempt to fetch/render
        # using the provided DB session or a short-lived session if none is given.
        try:
            if db is None:
                from app.db.connection_manager import AsyncSessionLocal
                async with AsyncSessionLocal() as temp_db:
                    rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "INTERVIEW_INVITE", context)
            else:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "INTERVIEW_INVITE", context)

            if rendered_subject and rendered_body:
                return await send_email_async(rendered_subject, to_email, rendered_body)
            else:
                # If templates are required by config, refuse to send.
                if getattr(settings, "email_require_templates", False):
                    logger.warning("INTERVIEW_INVITE template not found or empty; template-only mode enabled — refusing to send")
                    return False
                # Otherwise fall back to default inline HTML (tests/dev)
                logger.warning("INTERVIEW_INVITE template not found or empty; falling back to default inline interview invite email")
                if custom_subject and custom_body:
                    subject = _render_template(custom_subject, context)
                    html_body = _render_template(custom_body, context)
                else:
                    subject, html_body = get_default_interview_template_content()
                    html_body = _render_template(html_body, context)
                return await send_email_async(subject, to_email, html_body)
        except Exception as e:
            logger.error(f"Error fetching/rendering INTERVIEW_INVITE template: {e}")
            return False
    except Exception as e:
        logger.error(f"Async wrapper failed to send interview invite: {e}")
        return False
    
# --- NEW FUNCTION FOR RETRIEVING DEFAULT TEMPLATE CONTENT ---
def get_default_interview_template_content() -> tuple[str, str]:
    """
    Provides the placeholder strings for the default interview template.
    Used by the service layer when no custom template is saved.
    """
    default_subject = "Interview Invitation - {{JOB_TITLE}} at Smart HR Agent"
    
    # We use a placeholder version of the HTML body. 
    # For a true default, we use placeholders matching the f-string original structure
    default_html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h2 style="color: #0b2447; text-align: center;">Interview Invitation</h2>
            <p>Dear <strong>{{CANDIDATE_NAME}}</strong>,</p>

            <p>You have been shortlisted for the {{ROUND_NAME}} round for the {{JOB_TITLE}}</p>
            <p>The next round after this will be: <strong>{{NEXT_ROUND_NAME}}</strong></p>

            <p><strong>Scheduled Date & Time:</strong><br>{{INTERVIEW_TIME}}</p>
            <p><strong>Room ID:</strong> {{ROOM_CODE}}</p>

            <p>The interview link below will be active near the scheduled time. Use the Room ID to join.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{{JOIN_URL}}" style="background-color: #0b2447; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Join Interview</a>
            </div>

            <p style="margin-top: 40px;">
                Regards,<br>
                <strong>The RMS Team</strong>
            </p>
        </div>
    </body>
    </html>
    """
    return default_subject, default_html_body


# Default template for admin invite
def get_default_admin_invite_template_content() -> tuple[str, str]:
    subject = "Smart HR Agent - Admin Account Invitation"
    # Match the actual sent admin-invite HTML structure (use placeholders where dynamic)
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #4CAF50;">You're Invited: Admin Account Setup</h2>
            <p>Dear {{ADMIN_NAME}},</p>
            <p>You have been invited to create an <strong>Administrator account</strong> on the Smart HR Agent Portal.</p>
            <p>To finalize your account and choose a password, click the button below:</p>

            <div style="text-align: center; margin: 20px 0;">
                <a href="{{INVITE_LINK}}" target="_blank" style="display: inline-block; background-color: #0ea5e9; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">Complete Admin Setup</a>
            </div>

            <p style="margin-top: 8px;">{{EXPIRES_TEXT}}</p>
            <p style="font-size: 14px; color: #777;">If you did not expect this invitation, please disregard this email or contact your Super Administrator.</p>

            <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
            <p style="font-size: 14px; color: #777;">This is an automated message.</p>
            <p>Best regards,</p>
            <p>The RMS Management Team</p>
        </div>
    </body>
    </html>
    """
    return subject, body


def get_default_admin_role_update_template_content() -> tuple[str, str]:
    subject = "Important: Administrator Role Updated"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #0b2447;">Administrator Role Updated</h2>
                <p>Dear {{ADMIN_NAME}},</p>

                <p>Your administrator account role has been updated to <strong>{{NEW_ROLE}}</strong>.</p>
                <div style="background-color: #f1f5f9; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <p style="margin:0;"><strong>Previous role:</strong> {{OLD_ROLE}}</p>
                    <p style="margin:0;"><strong>New role:</strong> {{NEW_ROLE}}</p>
                </div>

                <p style="margin-top:12px;">{{PERFORMED_BY_TEXT}}</p>

                <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
                <p style="font-size: 14px; color: #777;">This is an automated notification. Please do not reply to this email.</p>
                <p>Best regards,</p>
                <p>The RMS Management Team</p>
            </div>
        </body>
    </html>
    """
    return subject, body


def get_default_admin_delete_template_content() -> tuple[str, str]:
    subject = "Important: Administrator Role Revoked"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #FF0000;">Admin Role Revoked</h2>
                <p>Dear {{ADMIN_NAME}}</p>
                <p>This is to formally notify you that your <strong>Administrator role</strong> on the Recruitment Management System (RMS) has been revoked by <strong>{{DELETED_BY_NAME}}</strong>.</p>

                <div style="background-color: #fcebeb; padding: 15px; border-radius: 5px; border: 1px solid #ebcccc;">
                    <p style="margin: 0; font-weight: bold; color: #c00;">ACTION TAKEN:</p>
                    <p style="margin: 5px 0 0 0;">Your account has been deactivated.</p>
                </div>

                <p style="margin-top: 20px;">If you believe this is an error or have any questions regarding this change, please contact your Super Administrator immediately.</p>

                <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
                <p style="font-size: 14px; color: #777;">This is an automated notification. Please do not reply to this email.</p>
                <p>Best regards,</p>
                <p>The RMS Management Team</p>
            </div>
        </body>
    </html>
    """
    return subject, body


# --- Additional default getters for other email flows ---
def get_default_otp_template_content() -> tuple[str, str]:
    subject = "Your One-Time Password (OTP) for RMS"
    # Match the exact OTP email design used by send_otp_email
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #4CAF50;">Welcome to Smart Interview Management Portal</h2>
            <p>To continue, please use the one-time password (OTP) below to securely access Smart Interview Management</p>
            <p style="font-size: 24px; font-weight: bold; color: #000; margin: 16px 0;">{{OTP_CODE}}</p>
            <p>This OTP is valid for <strong>{{OTP_EXPIRE_MINUTES}} minutes</strong>.</p>
            <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
            <p style="font-size: 14px; color: #777;">If you did not request this OTP, please disregard this message.</p>
        </div>
    </body>
    </html>
    """
    return subject, body


def get_default_email_update_verification_template_content() -> tuple[str, str]:
    subject = "Action Required: Complete Admin Email Transfer"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #4CAF50;">Admin Email Transfer Verification</h2>
            <p>Dear {{ADMIN_NAME}},</p>
            <p>A request was initiated by the <strong>Administrator account</strong> registered under <strong>{{OLD_EMAIL}}</strong> to transfer its admin permission to this email address (<strong>{{NEW_EMAIL}}</strong>).</p>
            <p>To <strong>confirm and finalize</strong> the transfer of the admin role to this new email, please click the button below:</p>

            <div style="text-align: center; margin: 20px 0;">
                <a href="{{VERIFICATION_LINK}}" target="_blank" style="display: inline-block; background-color: #0ea5e9; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">Confirm Email Transfer</a>
            </div>

            <p>{{EXPIRES_TEXT}}</p>
            <p style="font-size: 14px; color: #777;">If you did not initiate this change, <strong>DO NOT</strong> click the button and contact your Super Administrator immediately.</p>

            <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
            <p>Best regards,</p>
            <p>The RMS Management Team</p>
        </div>
    </body>
    </html>
    """
    return subject, body


def get_default_email_change_transfer_notification_template_content() -> tuple[str, str]:
        subject = "Security Alert: Admin Email Transfer Initiated"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border-radius: 8px; border: 1px solid #eee;">
                <h2 style="color: #FF4C00;">ACTION REQUIRED: Admin Permission Transfer</h2>
                <p>Dear {{ADMIN_NAME}},</p>
                <p>This is a security notification regarding your <strong>Administrator account</strong>.</p>
                <p>A request has been initiated to <strong>transfer the Admin permission</strong> currently associated with <strong>{{OLD_EMAIL}}</strong> to the new email address: <strong>{{NEW_EMAIL}}</strong>.</p>

                <div style="background-color: #fff8e1; padding: 15px; border-radius: 5px; border: 1px solid #ffe0b2;">
                        <p style="margin: 0; font-weight: bold; color: #ff9800;">TRANSFER STATUS:</p>
                        <p style="margin: 5px 0 0 0;">The transfer is <strong>PENDING</strong> confirmation at the new email address.</p>
                </div>

                {{APPROVAL_BLOCK}}

                <p style="margin-top: 20px;">If you initiated this change, no further action is required on this email. The transfer will complete once verified by <strong>{{NEW_EMAIL}}</strong>.</p>
                <p style="margin-top: 10px; font-weight: bold; color: #c00;">If you DID NOT request this transfer, please contact your Super Administrator immediately or reply to this email.</p>

                <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
                <p style="font-size: 14px; color: #777;">This is an automated notification.</p>
            </div>
        </body>
        </html>
        """
        return subject, body


def get_default_name_update_verification_template_content() -> tuple[str, str]:
    subject = "Action Required: Confirm Name Change on Your Profile"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #4CAF50;">Profile Name Update Verification</h2>
                <p>Dear {{OLD_NAME_FIRST}},</p>
                <p>A request was initiated to change your profile name on the Recruitment Management System:</p>

                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; border: 1px solid #c8e6c9; margin-bottom: 20px;">
                    <p style="margin: 0; font-weight: bold; color: #2e7d32;">Old Name: {{OLD_NAME}}</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: #016BAE;">New Name: {{NEW_NAME}}</p>
                </div>

                <p>To <strong>confirm and apply</strong> this name change to your admin account, please click the button below:</p>

                <div style="text-align: center; margin: 20px 0;">
                    <a href="{{VERIFICATION_LINK}}" target="_blank" style="display: inline-block; background-color: #0ea5e9; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">Confirm Name Change</a>
                </div>

                <p>{{EXPIRES_TEXT}}</p>
                <p style="font-size: 14px; color: #777;">If you did not initiate this change, <strong>DO NOT</strong> click the button and contact your Super Administrator immediately.</p>

                <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
                <p>Best regards,</p>
                <p>The RMS Management Team</p>
            </div>
        </body>
    </html>
    """
    return subject, body


def get_default_name_update_success_template_content() -> tuple[str, str]:
    subject = "Notification: Profile Name Successfully Updated"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #4CAF50;">Profile Name Confirmed</h2>
                <p>Dear {{FIRST_NAME}},</p>
                <p>Your admin profile name has been successfully updated to: <strong>{{NEW_NAME}}</strong>.</p>
                <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
                <p style="font-size: 14px; color: #777;">This is an automated notification.</p>
            </div>
        </body>
    </html>
    """
    return subject, body


def get_default_phone_update_verification_template_content() -> tuple[str, str]:
    subject = "Action Required: Confirm Phone Number Update"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #4CAF50;">Phone Number Update Confirmation</h2>
                <p>Dear {{ADMIN_NAME}},</p>
                <p>A request was submitted to update the phone number associated with your administrator account.</p>

                <div style="background-color: #f1f5f9; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; margin: 18px 0;">
                    <p style="margin: 0; font-weight: 600;">Current phone on record: <span style="color: #0f172a;">{{OLD_PHONE_DISPLAY}}</span></p>
                    <p style="margin: 8px 0 0 0; font-weight: 600;">Requested new phone number: <span style="color: #0f172a;">{{NEW_PHONE}}</span></p>
                </div>

                <p>To keep your account secure, please confirm this change by clicking the button below:</p>

                <div style="text-align: center; margin: 24px 0;">
                    <a href="{{VERIFICATION_LINK}}" target="_blank" style="display: inline-block; background-color: #0ea5e9; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">Confirm Phone Update</a>
                </div>

                <p>{{EXPIRES_TEXT}}</p>
                <p style="font-size: 14px; color: #64748b;">If you did not request this change, please contact your Super Administrator immediately.</p>

                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
                <p style="font-size: 14px; color: #64748b;">This is an automated notification. Do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    return subject, body


def get_default_otp_for_email_update_template_content() -> tuple[str, str]:
    subject = "Verify New Email Address (One-Time Password)"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #4CAF50;">Email Change Verification</h2>
            <p>Dear {{ADMIN_NAME}},</p>
            <p>To confirm your request to change your account's email address, please use the OTP below:</p>
            <p style="font-size: 24px; font-weight: bold; color: #000; margin: 16px 0;">{{OTP_CODE}}</p>
            <p>Enter this OTP on the verification screen to finalize your email change. This OTP is valid for <strong>{{OTP_EXPIRE_MINUTES}} minutes</strong>.</p>
            <p style="font-size: 14px; color: #777;">If you did not initiate this change, please ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
            <p>Best regards,</p>
            <p>The RMS Management Team</p>
        </div>
    </body>
    </html>
    """
    return subject, body
# NEW FUNCTION FOR PREVIEW API:
def get_preview_email_content(template_subject: str, template_body: str, sample_context: Dict[str, str | Any]) -> tuple[str, str]:
    """
    Renders the email subject and body using sample data for client-side preview.
    This is a synchronous function suitable for a FastAPI endpoint.
    """
    # Basic syntax validation to catch unbalanced handlebars which commonly
    # cause rendering to fail silently. Raise ValueError with a clear message
    # so the controller can return a 400 with that message to the client.
    def _validate_braces(s: str) -> None:
        if s is None:
            return
        open_count = s.count('{{')
        close_count = s.count('}}')
        if open_count != close_count:
            raise ValueError(f"Template syntax error: unmatched braces ({{{{ count={open_count}, }}}} count={close_count}).")

    _validate_braces(template_subject)
    _validate_braces(template_body)

    rendered_subject = _render_template(template_subject, sample_context)
    rendered_body = _render_template(template_body, sample_context)

    # Sanitize preview HTML to prevent scripts from being executed inside
    # sandboxed iframes (srcdoc) and to avoid browser console errors.
    def sanitize_html(html: str) -> str:
        if not html:
            return html
        # Remove <script>...</script> blocks (case-insensitive, DOTALL)
        html = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
        # Remove inline event handlers like onload=, onclick=, onerror= etc.
        html = re.sub(r'(?i)on[a-zA-Z]+\s*=\s*"[^"]*"', "", html)
        html = re.sub(r"(?i)on[a-zA-Z]+\s*=\s*'[^']*'", "", html)
        # Remove javascript: urls in href/src attributes
        html = re.sub(r'(?i)(href|src)\s*=\s*"javascript:[^"]*"', '\1="#"', html)
        html = re.sub(r"(?i)(href|src)\s*=\s*'javascript:[^']*'", "\1='#'", html)
        return html

    rendered_body = sanitize_html(rendered_body)
    rendered_subject = re.sub(r"(?is)<script.*?>.*?</script>", "", rendered_subject)

    return rendered_subject, rendered_body

def _send_email_sync(subject: str, recipient_email: str, html_content: str) -> bool:
    """
    Synchronous function containing the actual smtplib I/O.
    Runs off the main event loop via asyncio.to_thread.
    """
    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = recipient_email
    message["Subject"] = subject
   
    message.attach(MIMEText(html_content, "html"))
    context = ssl.create_default_context()
   
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
           
        return True
       
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"Failed to connect to SMTP server: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False
 
async def send_email_async(subject: str, recipient_email: str, html_content: str) -> bool:
    """Wraps the synchronous sender using asyncio.to_thread."""
    try:
        # Log for debugging purposes
        logger.info(f"Sending email to: {recipient_email}, Subject: {subject}")
       
        # Extract OTP from HTML content for debugging
        import re
        otp_match = re.search(r'<p style="[^"]*font-size: 24px[^"]*"[^>]*>([^<]+)</p>', html_content)
        if otp_match:
            otp_code = otp_match.group(1).strip()
            logger.info(f"OTP Code: {otp_code}")
       
        # Send actual email using SMTP
        result = await asyncio.to_thread(_send_email_sync, subject, recipient_email, html_content)
       
        if result:
            logger.info(f"Email sent successfully to {recipient_email}")
        else:
            logger.error(f"Failed to send email to {recipient_email}")
           
        return result
       
    except Exception as e:
        logger.error(f"Error in send_email_async: {e}")
        return False
    


 
async def send_otp_email(to_email: str, otp_code: str, subject: str, db: AsyncSession | None = None) -> bool:
    """Sends the OTP via email.

    If a DB session is provided and a saved template exists for key 'OTP', it will be
    rendered and used. Otherwise falls back to the inline HTML design.
    """
    # Context used for rendering templates
    context = {
        "OTP_CODE": otp_code,
        "OTP_EXPIRE_MINUTES": settings.otp_expire_seconds // 60,
    }

    # Require a saved template to send OTP emails. Attempt to fetch/render
    # using the provided DB session or a short-lived session if none is given.
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "OTP", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "OTP", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, to_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("OTP template not found or empty; template-only mode enabled — refusing to send")
                return False
            logger.warning("OTP template not found or empty; falling back to default inline OTP email")
            subject, html_body = get_default_otp_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, to_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering OTP template: {e}")
        return False
   
# simple older admin invite removed in favor of the full version below
async def send_admin_removal_email(recipient_email: str, admin_name: str | None = None, db: AsyncSession | None = None) -> bool:
    """Send admin removal notification. Prefer saved template when DB session provided."""

    subject = "Important: Administrator Role Revoked"
    admin_display_name = admin_name if admin_name and admin_name.strip() else "Valued User"

    context = {
        "ADMIN_NAME": admin_display_name,
        "DELETED_BY_NAME": "System",
    }

    # Require saved template for admin removal notification
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "ADMIN_DELETE", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "ADMIN_DELETE", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, recipient_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("ADMIN_DELETE template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("ADMIN_DELETE template not found; falling back to default inline admin removal email")
            subject, html_body = get_default_admin_delete_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, recipient_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering ADMIN_DELETE template: {e}")
        return False
 



async def send_email_async(subject: str, recipient_email: str, html_content: str) -> bool:
    """Wraps the synchronous sender using asyncio.to_thread."""
    try:
        # Log for debugging purposes
        logger.info(f"Sending email to: {recipient_email}, Subject: {subject}")
        
        # Extract OTP from HTML content for debugging
        import re
        otp_match = re.search(r'<p style="[^"]*font-size: 24px[^"]*"[^>]*>([^<]+)</p>', html_content)
        if otp_match:
            otp_code = otp_match.group(1).strip()
            logger.info(f"OTP Code: {otp_code}")
        
        # Send actual email using SMTP
        result = await asyncio.to_thread(_send_email_sync, subject, recipient_email, html_content)
        
        if result:
            logger.info(f"Email sent successfully to {recipient_email}")
        else:
            logger.error(f"Failed to send email to {recipient_email}")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in send_email_async: {e}")
        return False
 

   
async def send_admin_invite_email(
    to_email: str,
    admin_name: str,
    invite_link: str,
    expires_at: Optional[datetime] = None,
    db: AsyncSession | None = None,
) -> bool:
    """Sends the admin invitation link; prefer saved template when available."""

    subject = "Smart HR Agent - Admin Account Invitation"

    # Format expiry display if provided
    expires_display = None
    try:
        if expires_at:
            # If naive datetime assume UTC
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            # Convert to display timezone (IST in this project)
            local_dt = expires_at.astimezone(DISPLAY_TIMEZONE)
            expires_display = local_dt.strftime('%d %b %Y, %I:%M %p') + ' (IST)'
    except Exception as e:
        logger.warning(f"Failed to format expires_at for invite email: {e}")

    expires_text = f"This link will expire on <strong>{expires_display}</strong>." if expires_display else f"This link will expire in <strong>{settings.otp_expire_seconds//60} minutes</strong>."

    # Context for rendering saved template
    context = {
        "ADMIN_NAME": admin_name,
        "INVITE_LINK": invite_link,
        "EXPIRES_TEXT": expires_text,
    }

    # Require saved template for admin invite
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "ADMIN_INVITE", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "ADMIN_INVITE", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, to_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("ADMIN_INVITE template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("ADMIN_INVITE template not found; falling back to default inline admin invite email")
            subject, html_body = get_default_admin_invite_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, to_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering ADMIN_INVITE template: {e}")
        return False
   



async def send_admin_role_change_email(recipient_email: str, admin_name: str | None, old_role: str, new_role: str, performed_by: str | None = None, db: AsyncSession | None = None) -> bool:
    """Sends a notification email to the admin when their role is changed (promotion/demotion).

    This re-uses the admin email visual style and includes who performed the action.
    Failures to send should not block the main action.
    """
    try:
        promoted = False
        roles_order = ['HR', 'ADMIN', 'SUPER_ADMIN']
        try:
            promoted = roles_order.index(new_role) > roles_order.index(old_role)
        except Exception:
            promoted = new_role != old_role

        subject_action = 'Promoted' if promoted else 'Demoted' if old_role != new_role else 'Updated'
        subject = f"Important: Administrator Role {subject_action}"

        admin_display_name = admin_name if admin_name and admin_name.strip() else 'Valued User'

        performed_by_text = f"This change was performed by {performed_by}." if performed_by else ''

        # Choose colors and wording depending on promotion vs demotion
        if promoted:
            header_color = '#2e7d32'  # green
            banner_bg = '#e8f5e9'
            banner_border = '#c8e6c9'
            action_text = 'promoted to'
        else:
            header_color = '#c62828'  # red
            banner_bg = '#fff0f0'
            banner_border = '#ebcccc'
            action_text = 'demoted to'

        html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                        <h2 style="color: {header_color};">Administrator Role {subject_action}</h2>
                        <p>Dear {admin_display_name},</p>

                        <p>Your administrator account role has been <strong>{action_text} {format_role_subject(new_role)}</strong>. For your security, you will need to sign in again to continue using the system.</p>

                        <div style="background-color: {banner_bg}; padding: 12px; border-radius: 6px; border: 1px solid {banner_border};">
                            <p style="margin:0;"><strong>Previous role:</strong> {format_role_subject(old_role)}</p>
                            <p style="margin:0;"><strong>New role:</strong> {format_role_subject(new_role)}</p>
                        </div>

                        <p style="margin-top:12px;">{performed_by_text}</p>

                        <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
                        <p style="font-size: 14px; color: #777;">This is an automated notification. Please do not reply to this email.</p>
                        <p>Best regards,</p>
                        <p>The RMS Management Team</p>
                    </div>
                </body>
            </html>
            """

        # Require saved template for role-change notification
        try:
            if db is None:
                from app.db.connection_manager import AsyncSessionLocal
                async with AsyncSessionLocal() as temp_db:
                    rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "ADMIN_ROLE_CHANGE", {
                        "ADMIN_NAME": admin_display_name,
                        "OLD_ROLE": old_role,
                        "NEW_ROLE": new_role,
                        "PERFORMED_BY": performed_by or "",
                        "PERFORMED_BY_TEXT": performed_by_text or "",
                    })
            else:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "ADMIN_ROLE_CHANGE", {
                    "ADMIN_NAME": admin_display_name,
                    "OLD_ROLE": old_role,
                    "NEW_ROLE": new_role,
                    "PERFORMED_BY": performed_by or "",
                    "PERFORMED_BY_TEXT": performed_by_text or "",
                })

            if rendered_subject and rendered_body:
                return await send_email_async(rendered_subject, recipient_email, rendered_body)
            else:
                if getattr(settings, "email_require_templates", False):
                    logger.warning("ADMIN_ROLE_CHANGE template not found; template-only mode enabled — refusing to send")
                    return False
                logger.warning("ADMIN_ROLE_CHANGE template not found; falling back to default inline role-change email")
                subject, html_body = get_default_admin_role_update_template_content()
                html_body = _render_template(html_body, {
                    "ADMIN_NAME": admin_display_name,
                    "OLD_ROLE": old_role,
                    "NEW_ROLE": new_role,
                    "PERFORMED_BY": performed_by or "",
                    "PERFORMED_BY_TEXT": performed_by_text or "",
                })
                return await send_email_async(subject, recipient_email, html_body)
        except Exception as e:
            logger.error(f"Error fetching/rendering ADMIN_ROLE_CHANGE template: {e}")
            return False
    except Exception as e:
        logger.error(f"Failed to send role change email to {recipient_email}: {e}")
        return False


def format_role_subject(role: str) -> str:
    if role == 'SUPER_ADMIN':
        return 'Super Admin'
    if role == 'ADMIN':
        return 'Admin'
    if role == 'HR':
        return 'HR'
    return role
 
async def send_email_update_verification_link(
    recipient_email: str,
    admin_name: str,
    verification_link: str,
    old_email: str,
    api_info: dict = None,
    expires_at: Optional[datetime] = None,
    db: AsyncSession | None = None,
) -> bool:
    """
    Sends a verification link to the admin's new email for update confirmation (Email 2).
    Uses the common button-style template and accepts an optional expires_at to display expiry text.
    """

    subject = "Action Required: Complete Admin Email Transfer"

    # Format expiry display if provided. Capture any formatting exception so
    # it can be logged later without referencing an out-of-scope variable.
    expires_display = None
    expires_format_error = None
    try:
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            local_dt = expires_at.astimezone(DISPLAY_TIMEZONE)
            expires_display = local_dt.strftime('%d %b %Y, %I:%M %p') + ' (IST)'
    except Exception as e:
        # Ignore issues when computing local display; keep expires_display as None
        expires_format_error = e

    # If api_info is provided include a small debug hint in the subject so
    # callers and logs can correlate the email with the verification API call.
    if api_info:
        try:
            endpoint = api_info.get("endpoint") if isinstance(api_info, dict) else None
            if endpoint:
                subject += f" [{endpoint.split('/')[-1]}]"
        except Exception:
            pass

        # Only log if we actually encountered an earlier formatting error.
        if expires_format_error:
            logger.warning(f"Failed to format expires_at for update verification email: {expires_format_error}")

    expires_text = f"This verification link will expire on <strong>{expires_display}</strong>." if expires_display else f"This verification link will expire in <strong>{settings.invite_expire_minutes} minutes</strong>."

    # Context for saved template rendering
    context = {
        "ADMIN_NAME": admin_name,
        "VERIFICATION_LINK": verification_link,
        "OLD_EMAIL": old_email,
        "NEW_EMAIL": recipient_email,
        "EXPIRES_TEXT": expires_text,
    }

    # Require saved template for update verification emails
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "EMAIL_UPDATE_VERIFICATION", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "EMAIL_UPDATE_VERIFICATION", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, recipient_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("EMAIL_UPDATE_VERIFICATION template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("EMAIL_UPDATE_VERIFICATION template not found; falling back to default inline update verification email")
            subject, html_body = get_default_email_update_verification_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, recipient_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering EMAIL_UPDATE_VERIFICATION template: {e}")
        return False
 
async def send_email_change_transfer_notification(old_email: str, admin_name: str, new_email: str, approval_link: str | None = None, expires_at: Optional[datetime] = None, db: AsyncSession | None = None) -> bool:
    """
    Sends a notification to the old email that admin permission is being transferred (Email 1).
    Optionally includes an approval link (if provided) so the current admin can approve the transfer.
    """
    subject = "Security Alert: Admin Email Transfer Initiated"
    approval_block = ""
    if approval_link:
        approval_block = f"""

                <div style=\"margin: 24px 0;\">\n                    <a href=\"{approval_link}\" target=\"_blank\" style=\"display: inline-block; background-color: #FF4C00; color: #ffffff; padding: 12px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;\">Approve Email Transfer</a>
                </div>
        """

    # Format expiry display if provided
    expires_display = None
    try:
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            local_dt = expires_at.astimezone(DISPLAY_TIMEZONE)
            expires_display = local_dt.strftime('%d %b %Y, %I:%M %p') + ' (IST)'
    except Exception as e:
        logger.warning(f"Failed to format expires_at for email transfer notification: {e}")

    expires_text = f"This link will expire on <strong>{expires_display}</strong>." if expires_display else f"This link will expire in <strong>{settings.invite_expire_minutes} minutes</strong>."

    # Try to use saved template
    context = {
        "ADMIN_NAME": admin_name,
        "OLD_EMAIL": old_email,
        "NEW_EMAIL": new_email,
        "APPROVAL_BLOCK": approval_block,
        "EXPIRES_TEXT": expires_text,
    }

    # Require saved template for transfer notification
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "EMAIL_CHANGE_TRANSFER_NOTIFICATION", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "EMAIL_CHANGE_TRANSFER_NOTIFICATION", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, old_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("EMAIL_CHANGE_TRANSFER_NOTIFICATION template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("EMAIL_CHANGE_TRANSFER_NOTIFICATION template not found; falling back to default inline transfer notification email")
            subject, html_body = get_default_email_change_transfer_notification_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, old_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering EMAIL_CHANGE_TRANSFER_NOTIFICATION template: {e}")
        return False
 
 
async def send_name_update_verification_link(recipient_email: str, old_name: str, new_name: str, verification_link: str, expires_at: Optional[datetime] = None, db: AsyncSession | None = None) -> bool:
    """Sends a verification link to the admin's email to confirm a name change using the unified button template."""
    subject = "Action Required: Confirm Name Change on Your Profile"

    expires_display = None
    try:
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            local_dt = expires_at.astimezone(DISPLAY_TIMEZONE)
            expires_display = local_dt.strftime('%d %b %Y, %I:%M %p') + ' (IST)'
    except Exception as e:
        logger.warning(f"Failed to format expires_at for name update email: {e}")

    expires_text = f"This verification link will expire on <strong>{expires_display}</strong>." if expires_display else f"This verification link will expire in <strong>{settings.invite_expire_minutes} minutes</strong>."

    context = {
        "OLD_NAME": old_name,
        "OLD_NAME_FIRST": old_name.split()[0] if old_name else "",
        "NEW_NAME": new_name,
        "VERIFICATION_LINK": verification_link,
        "EXPIRES_TEXT": expires_text,
    }

    # Require saved template for name-update verification
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "NAME_UPDATE_VERIFICATION", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "NAME_UPDATE_VERIFICATION", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, recipient_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("NAME_UPDATE_VERIFICATION template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("NAME_UPDATE_VERIFICATION template not found; falling back to default inline name-update verification email")
            subject, html_body = get_default_name_update_verification_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, recipient_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering NAME_UPDATE_VERIFICATION template: {e}")
        return False
 
async def send_name_update_success_notification(recipient_email: str, new_name: str, db: AsyncSession | None = None) -> bool:
    """
    Sends a final notification confirming the name change is complete; uses saved template if available.
    """
    subject = "Notification: Profile Name Successfully Updated"
    context = {
        "FIRST_NAME": new_name.split()[0] if new_name else "",
        "NEW_NAME": new_name,
    }

    # Require saved template for name-update success notification
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "NAME_UPDATE_SUCCESS", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "NAME_UPDATE_SUCCESS", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, recipient_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("NAME_UPDATE_SUCCESS template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("NAME_UPDATE_SUCCESS template not found; falling back to default inline name-update success email")
            subject, html_body = get_default_name_update_success_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, recipient_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering NAME_UPDATE_SUCCESS template: {e}")
        return False
 
async def send_phone_update_verification_link(
    recipient_email: str,
    admin_name: str,
    old_phone: str | None,
    new_phone: str,
    verification_link: str,
    expires_at: Optional[datetime] = None,
    db: AsyncSession | None = None,
) -> bool:
    """Send a confirmation email for pending phone number updates using the unified template."""

    safe_admin_name = admin_name.strip() or "Admin"
    old_phone_display = old_phone.strip() if old_phone else "Not previously provided"

    expires_display = None
    try:
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            local_dt = expires_at.astimezone(DISPLAY_TIMEZONE)
            expires_display = local_dt.strftime('%d %b %Y, %I:%M %p') + ' (IST)'
    except Exception as e:
        logger.warning(f"Failed to format expires_at for phone update email: {e}")

    expires_text = f"This confirmation link will expire on <strong>{expires_display}</strong>." if expires_display else f"This confirmation link will expire in <strong>{settings.invite_expire_minutes} minutes</strong>."

    subject = "Action Required: Confirm Phone Number Update"

    context = {
        "ADMIN_NAME": admin_name,
        "OLD_PHONE_DISPLAY": old_phone_display,
        "NEW_PHONE": new_phone,
        "VERIFICATION_LINK": verification_link,
        "EXPIRES_TEXT": expires_text,
    }

    # Require saved template for phone-update verification
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "PHONE_UPDATE_VERIFICATION", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "PHONE_UPDATE_VERIFICATION", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, recipient_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("PHONE_UPDATE_VERIFICATION template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("PHONE_UPDATE_VERIFICATION template not found; falling back to default inline phone-update verification email")
            subject, html_body = get_default_phone_update_verification_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, recipient_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering PHONE_UPDATE_VERIFICATION template: {e}")
        return False

async def send_otp_for_email_update(recipient_email: str, admin_name: str, otp_code: str, db: AsyncSession | None = None) -> bool:
    """Sends an OTP to the user's new email for update confirmation (for Admin/Candidate self-update)."""
   
    subject = "Verify New Email Address (One-Time Password)"

    context = {
        "ADMIN_NAME": admin_name,
        "OTP_CODE": otp_code,
        "OTP_EXPIRE_MINUTES": settings.otp_expire_seconds // 60,
    }

    # Require saved template for OTP for email update
    try:
        if db is None:
            from app.db.connection_manager import AsyncSessionLocal
            async with AsyncSessionLocal() as temp_db:
                rendered_subject, rendered_body = await _fetch_and_render_saved_template(temp_db, "OTP_FOR_EMAIL_UPDATE", context)
        else:
            rendered_subject, rendered_body = await _fetch_and_render_saved_template(db, "OTP_FOR_EMAIL_UPDATE", context)

        if rendered_subject and rendered_body:
            return await send_email_async(rendered_subject, recipient_email, rendered_body)
        else:
            if getattr(settings, "email_require_templates", False):
                logger.warning("OTP_FOR_EMAIL_UPDATE template not found; template-only mode enabled — refusing to send")
                return False
            logger.warning("OTP_FOR_EMAIL_UPDATE template not found; falling back to default inline OTP for email update")
            subject, html_body = get_default_otp_for_email_update_template_content()
            html_body = _render_template(html_body, context)
            return await send_email_async(subject, recipient_email, html_body)
    except Exception as e:
        logger.error(f"Error fetching/rendering OTP_FOR_EMAIL_UPDATE template: {e}")
        return False


