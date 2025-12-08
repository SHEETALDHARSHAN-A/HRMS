import pytest
import asyncio

from app.utils import email_utils as eu


SEND_FUNCS = [
    (eu.send_otp_email, ("a@b.com", "1234", "subj")),
    (eu.send_admin_removal_email, ("a@b.com", "Admin")),
    (eu.send_admin_invite_email, ("a@b.com", "Admin", "http://inv")),
    (eu.send_admin_role_change_email, ("a@b.com", "Admin", "HR", "ADMIN")),
    (eu.send_email_update_verification_link, ("a@b.com", "Admin", "http://v", "old@e")),
    (eu.send_email_change_transfer_notification, ("old@e", "Admin", "new@e")),
    (eu.send_name_update_verification_link, ("a@b.com", "Old Name", "New Name", "http://v")),
    (eu.send_name_update_success_notification, ("a@b.com", "New Name")),
    (eu.send_phone_update_verification_link, ("a@b.com", "Admin", None, "999", "http://v")),
    (eu.send_otp_for_email_update, ("a@b.com", "Admin", "4321")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("func, args", SEND_FUNCS)
async def test_send_funcs_saved_template_and_fallback(monkeypatch, func, args):
    """For each send_* function: test saved-template path and fallback/template-only behaviors."""

    async def saved_fetch(db, key, ctx):
        return ("S", "<p>B</p>")

    async def none_fetch(db, key, ctx):
        return (None, None)

    async def fake_send(subject, recipient, html):
        return True

    # Saved-template path -> should return True
    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', saved_fetch)
    monkeypatch.setattr(eu, 'send_email_async', fake_send)

    res = await func(*args, db='DB') if asyncio.iscoroutinefunction(func) else await func(*args, db='DB')
    assert res is True

    # Missing template + template-only enabled -> should return False
    monkeypatch.setattr(eu, '_fetch_and_render_saved_template', none_fetch)
    prev = getattr(eu.settings, 'email_require_templates', False)
    eu.settings.email_require_templates = True

    res2 = await func(*args, db='DB') if asyncio.iscoroutinefunction(func) else await func(*args, db='DB')
    assert res2 is False

    # Missing template + template-only disabled -> fallback to send_email_async
    eu.settings.email_require_templates = False
    res3 = await func(*args, db='DB') if asyncio.iscoroutinefunction(func) else await func(*args, db='DB')
    assert res3 is True

    eu.settings.email_require_templates = prev
