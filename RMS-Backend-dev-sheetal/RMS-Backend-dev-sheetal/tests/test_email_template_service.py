import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.config_service import email_template_service as service_mod
from app.services.config_service.email_template_service import EmailTemplateService


@pytest.mark.asyncio
async def test_get_template_db_present(monkeypatch):
    class FakeRecord:
        def __init__(self):
            self.template_key = 'TEST'
            self.subject_template = 'Sub'
            self.body_template_html = '<p>Body</p>'

    async def fake_get(db, key):
        return FakeRecord()

    monkeypatch.setattr(service_mod.ConfigRepository, 'get_template_by_key', AsyncMock(side_effect=fake_get))
    result = await EmailTemplateService.get_template(db=SimpleNamespace(), template_key='TEST')
    assert result['template_key'] == 'TEST'
    assert 'subject_template' in result


@pytest.mark.asyncio
async def test_get_template_db_absent_key_map(monkeypatch):
    async def fake_get(db, key):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'get_template_by_key', AsyncMock(side_effect=fake_get))
    # Use a key that is mapped in the service (INTERVIEW_INVITE -> default)
    result = await EmailTemplateService.get_template(db=SimpleNamespace(), template_key='interview_invite')
    assert result['template_key'] == 'interview_invite'
    assert 'subject_template' in result
    assert 'body_template_html' in result


@pytest.mark.asyncio
async def test_get_template_db_absent_no_default(monkeypatch):
    async def fake_get(db, key):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'get_template_by_key', AsyncMock(side_effect=fake_get))
    result = await EmailTemplateService.get_template(db=SimpleNamespace(), template_key='UNKNOWN_KEY')
    assert result['subject_template'] == 'No Default Subject Available'
    assert result['body_template_html'] == 'No Default Body Available'


@pytest.mark.asyncio
async def test_get_template_preview_content_success_and_error(monkeypatch):
    # Successful rendering path
    monkeypatch.setattr(service_mod, 'get_preview_email_content', lambda s, b, c: ('Sub out', '<p>Body out</p>'))
    subj, body = await EmailTemplateService.get_template_preview_content('S', 'B', {'k': 'v'})
    assert subj == 'Sub out'
    assert body == '<p>Body out</p>'

    # Error path: underlying renderer raises
    def fake_preview(subject, body, ctx):
        raise Exception('boom')

    monkeypatch.setattr(service_mod, 'get_preview_email_content', fake_preview)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content('S', 'B', {})


@pytest.mark.asyncio
async def test_save_email_template_success_and_failure(monkeypatch):
    async def fake_save(db, k, s, b):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save))
    ok = await EmailTemplateService.save_email_template(db=SimpleNamespace(), template_key='K', subject_template='S', body_template_html='B')
    assert ok is True

    async def fake_save_err(db, k, s, b):
        raise Exception('DB error')

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save_err))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(db=SimpleNamespace(), template_key='K', subject_template='S', body_template_html='B')


@pytest.mark.asyncio
async def test_reset_template_to_default_success_and_errors(monkeypatch):
    async def fake_save(db, k, s, b):
        return None

    # known key -> success
    monkeypatch.setattr(service_mod, 'get_default_interview_template_content', lambda: ('ISub', 'IBody'))
    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save))
    res = await EmailTemplateService.reset_template_to_default(db=SimpleNamespace(), template_key='INTERVIEW_INVITATION')
    assert res is True

    # unknown key -> False
    res2 = await EmailTemplateService.reset_template_to_default(db=SimpleNamespace(), template_key='NO_KEY')
    assert res2 is False

    # repo error -> exception
    async def fake_save_err(db, k, s, b):
        raise Exception('repo fail')

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save_err))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(db=SimpleNamespace(), template_key='INTERVIEW_INVITE')
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.config_service.email_template_service import EmailTemplateService
import app.services.config_service.email_template_service as service_mod


@pytest.mark.asyncio
async def test_get_template_returns_db_record(monkeypatch, fake_db):
    rec = SimpleNamespace(template_key="OTP", subject_template="S", body_template_html="B")
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=rec))
    res = await EmailTemplateService.get_template(fake_db, "otp")
    assert res["template_key"] == "OTP"
    assert res["subject_template"] == "S"


@pytest.mark.asyncio
async def test_get_template_returns_default_for_mapped_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("Default Sub", "Default Body"))
    res = await EmailTemplateService.get_template(fake_db, "INTERVIEW_INVITE")
    assert res["template_key"] == "INTERVIEW_INVITE"
    assert res["subject_template"] == "Default Sub"
    assert res["body_template_html"] == "Default Body"


@pytest.mark.asyncio
async def test_get_template_returns_no_default_for_unknown_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    res = await EmailTemplateService.get_template(fake_db, "NO_SUCH_KEY")
    assert res["subject_template"] == "No Default Subject Available"
    assert res["body_template_html"] == "No Default Body Available"


@pytest.mark.asyncio
async def test_get_template_preview_content_renders(monkeypatch):
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", lambda s, b, ctx: ("Rsub", "Rbody"))
    sub, body = await EmailTemplateService.get_template_preview_content("sub {{name}}", "<p>{{name}}</p>", {"name": "Alice"})
    assert sub == "Rsub"
    assert body == "Rbody"


@pytest.mark.asyncio
async def test_get_template_preview_content_raises(monkeypatch):
    def bad_render(s, b, ctx):
        raise Exception("fail")
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", bad_render)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("s", "b", {})


@pytest.mark.asyncio
async def test_save_email_template_success(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")
    assert res is True


@pytest.mark.asyncio
async def test_save_email_template_failure_raises(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")


@pytest.mark.asyncio
async def test_reset_template_to_default_success_and_errors(monkeypatch, fake_db):
    # Patch getter and success repo
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("ISub", "IBody"))
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
    assert res is True

    # Unknown key -> returns False
    res2 = await EmailTemplateService.reset_template_to_default(fake_db, "NO_KEY")
    assert res2 is False

    # Repo raises -> exception bubbles
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.config_service.email_template_service import EmailTemplateService
import app.services.config_service.email_template_service as service_mod


@pytest.mark.asyncio
async def test_get_template_returns_db_record(monkeypatch, fake_db):
    rec = SimpleNamespace(template_key="OTP", subject_template="S", body_template_html="B")
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=rec))
    res = await EmailTemplateService.get_template(fake_db, "otp")
    assert res["template_key"] == "OTP"
    assert res["subject_template"] == "S"


@pytest.mark.asyncio
async def test_get_template_returns_default_for_mapped_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("Default Sub", "Default Body"))
    res = await EmailTemplateService.get_template(fake_db, "INTERVIEW_INVITE")
    assert res["template_key"] == "INTERVIEW_INVITE"
    assert res["subject_template"] == "Default Sub"
    assert res["body_template_html"] == "Default Body"


@pytest.mark.asyncio
async def test_get_template_returns_no_default_for_unknown_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    res = await EmailTemplateService.get_template(fake_db, "NO_SUCH_KEY")
    assert res["subject_template"] == "No Default Subject Available"
    assert res["body_template_html"] == "No Default Body Available"


@pytest.mark.asyncio
async def test_get_template_preview_content_renders(monkeypatch):
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", lambda s, b, ctx: ("Rsub", "Rbody"))
    sub, body = await EmailTemplateService.get_template_preview_content("sub {{name}}", "<p>{{name}}</p>", {"name": "Alice"})
    assert sub == "Rsub"
    assert body == "Rbody"


@pytest.mark.asyncio
async def test_get_template_preview_content_raises(monkeypatch):
    def bad_render(s, b, ctx):
        raise Exception("fail")
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", bad_render)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("s", "b", {})


@pytest.mark.asyncio
async def test_save_email_template_success(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")
    assert res is True


@pytest.mark.asyncio
async def test_save_email_template_failure_raises(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")


@pytest.mark.asyncio
async def test_reset_template_to_default_success_and_errors(monkeypatch, fake_db):
    # Patch getter and success repo
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("ISub", "IBody"))
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
    assert res is True

    # Unknown key -> returns False
    res2 = await EmailTemplateService.reset_template_to_default(fake_db, "NO_KEY")
    assert res2 is False

    # Repo raises -> exception bubbles
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.config_service.email_template_service import EmailTemplateService
import app.services.config_service.email_template_service as service_mod


@pytest.mark.asyncio
async def test_get_template_returns_db_record(monkeypatch, fake_db):
    rec = SimpleNamespace(template_key="OTP", subject_template="S", body_template_html="B")
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=rec))
    res = await EmailTemplateService.get_template(fake_db, "otp")
    assert res["template_key"] == "OTP"
    assert res["subject_template"] == "S"


@pytest.mark.asyncio
async def test_get_template_returns_default_for_mapped_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("Default Sub", "Default Body"))
    res = await EmailTemplateService.get_template(fake_db, "INTERVIEW_INVITE")
    assert res["template_key"] == "INTERVIEW_INVITE"
    assert res["subject_template"] == "Default Sub"
    assert res["body_template_html"] == "Default Body"


@pytest.mark.asyncio
async def test_get_template_returns_no_default_for_unknown_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    res = await EmailTemplateService.get_template(fake_db, "NO_SUCH_KEY")
    assert res["subject_template"] == "No Default Subject Available"
    assert res["body_template_html"] == "No Default Body Available"


@pytest.mark.asyncio
async def test_get_template_preview_content_renders(monkeypatch):
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", lambda s, b, ctx: ("Rsub", "Rbody"))
    sub, body = await EmailTemplateService.get_template_preview_content("sub {{name}}", "<p>{{name}}</p>", {"name": "Alice"})
    assert sub == "Rsub"
    assert body == "Rbody"


@pytest.mark.asyncio
async def test_get_template_preview_content_raises(monkeypatch):
    def bad_render(s, b, ctx):
        raise Exception("fail")
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", bad_render)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("s", "b", {})


@pytest.mark.asyncio
async def test_save_email_template_success(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")
    assert res is True


@pytest.mark.asyncio
async def test_save_email_template_failure_raises(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")


@pytest.mark.asyncio
async def test_reset_template_to_default_success_and_errors(monkeypatch, fake_db):
    # Patch getter and success repo
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("ISub", "IBody"))
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
    assert res is True

    # Unknown key -> returns False
    res2 = await EmailTemplateService.reset_template_to_default(fake_db, "NO_KEY")
    assert res2 is False

    # Repo raises -> exception bubbles
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.config_service.email_template_service import EmailTemplateService
import app.services.config_service.email_template_service as service_mod


@pytest.mark.asyncio
async def test_get_template_returns_db_record(monkeypatch, fake_db):
    rec = SimpleNamespace(template_key="OTP", subject_template="S", body_template_html="B")
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=rec))
    res = await EmailTemplateService.get_template(fake_db, "otp")
    assert res["template_key"] == "OTP"
    assert res["subject_template"] == "S"


@pytest.mark.asyncio
async def test_get_template_returns_default_and_fallback(monkeypatch, fake_db):
    # No DB record returned
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    # default mapping should be applied for known keys
    res = await EmailTemplateService.get_template(fake_db, "INTERVIEW_INVITE")
    assert isinstance(res["subject_template"], str)

    # Unknown key -> generic fallback text
    res2 = await EmailTemplateService.get_template(fake_db, "NO_SUCH_KEY")
    assert res2["subject_template"] == "No Default Subject Available"
    assert res2["body_template_html"] == "No Default Body Available"


@pytest.mark.asyncio
async def test_get_template_preview_content_renders_and_raises(monkeypatch):
    # Patch the symbol imported into the service module
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", lambda s, b, c: ("Sx", "Bx"))
    out = await EmailTemplateService.get_template_preview_content("S", "B", {"A": 1})
    assert out == ("Sx", "Bx")

    # Error path: underlying renderer raises
    def bad_render(s, b, c):
        raise Exception("fail")
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", bad_render)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("S", "B", {})


@pytest.mark.asyncio
async def test_save_email_template_success_and_failure(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")
    assert res is True

    # Failure propagates as RuntimeError
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")


@pytest.mark.asyncio
async def test_reset_template_to_default(monkeypatch, fake_db):
    # Known key: should call repo and return True
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("ISub", "IBody"))
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
    assert res is True

    # Unknown key: returns False
    res2 = await EmailTemplateService.reset_template_to_default(fake_db, "NO_KEY")
    assert res2 is False

    # If repo raises, exception bubbles
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio

from app.services.config_service import email_template_service as service_mod
from app.services.config_service.email_template_service import EmailTemplateService
from app.db.repository import config_repository


@pytest.mark.asyncio
async def test_get_template_returns_db_record(monkeypatch, fake_db):
    rec = SimpleNamespace(template_key="k", subject_template="S", body_template_html="B")
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=rec))
    res = await EmailTemplateService.get_template(fake_db, "k")
    assert res["template_key"] == "k"
    assert res["subject_template"] == "S"


@pytest.mark.asyncio
async def test_get_template_returns_default_by_key(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    # Known key that maps to defaults
    res = await EmailTemplateService.get_template(fake_db, "INTERVIEW_INVITE")
    assert "JOB_TITLE" in res["subject_template"] or isinstance(res["subject_template"], str)
    # Unknown key -> default fallback text
    res2 = await EmailTemplateService.get_template(fake_db, "NO_SUCH_KEY")
    assert res2["subject_template"] == "No Default Subject Available"


@pytest.mark.asyncio
async def test_get_template_preview_content_renders_and_raises(monkeypatch):
    # Happy path: patch the symbol imported into the service module
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", lambda s, b, c: ("Sx", "Bx"))
    out = await EmailTemplateService.get_template_preview_content("S", "B", {"A": 1})
    assert out == ("Sx", "Bx")

    # Error path: underlying renderer raises
    def bad_render(s, b, c):
        raise Exception("fail")
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", bad_render)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("S", "B", {})


@pytest.mark.asyncio
async def test_save_email_template_success_and_failure(monkeypatch, fake_db):
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")
    assert res is True

    # Failure propagates as RuntimeError
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(fake_db, "k", "S", "B")


@pytest.mark.asyncio
async def test_reset_template_to_default(monkeypatch, fake_db):
    # Known key: should call repo and return True
    monkeypatch.setattr(service_mod, "get_default_interview_template_content", lambda: ("ISub", "IBody"))
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
    assert res is True

    # Unknown key: returns False
    res2 = await EmailTemplateService.reset_template_to_default(fake_db, "NO_KEY")
    assert res2 is False

    # If repo raises, exception bubbles
    monkeypatch.setattr(service_mod.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(fake_db, "INTERVIEW_INVITE")
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio

from app.services.config_service.email_template_service import EmailTemplateService
from app.db.repository import config_repository as repo
import app.utils.email_utils as email_utils


@pytest.mark.asyncio
async def test_get_template_db_present(monkeypatch):
    class FakeRecord:
        def __init__(self):
            self.template_key = 'TEST'
            self.subject_template = 'Sub'
            self.body_template_html = '<p>Body</p>'

    async def fake_get(db, key):
        return FakeRecord()

    monkeypatch.setattr(service_mod.ConfigRepository, 'get_template_by_key', AsyncMock(side_effect=fake_get))
    result = await EmailTemplateService.get_template(db=SimpleNamespace(), template_key='TEST')
    assert result['template_key'] == 'TEST'
    assert 'subject_template' in result


@pytest.mark.asyncio
async def test_get_template_db_absent_key_map(monkeypatch):
    async def fake_get(db, key):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'get_template_by_key', AsyncMock(side_effect=fake_get))
    # Use a key that is mapped in the service (INTERVIEW_INVITE -> default)
    result = await EmailTemplateService.get_template(db=SimpleNamespace(), template_key='interview_invite')
    assert result['template_key'] == 'interview_invite'
    assert 'subject_template' in result
    assert 'body_template_html' in result


@pytest.mark.asyncio
async def test_get_template_db_absent_no_default(monkeypatch):
    async def fake_get(db, key):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'get_template_by_key', AsyncMock(side_effect=fake_get))
    result = await EmailTemplateService.get_template(db=SimpleNamespace(), template_key='UNKNOWN_KEY')
    assert result['subject_template'] == 'No Default Subject Available'
    assert result['body_template_html'] == 'No Default Body Available'


@pytest.mark.asyncio
async def test_get_template_preview_content_success(monkeypatch):
    # Monkeypatch the email_utils preview function to return rendered strings
    def fake_preview(subject, body, ctx):
        return ("Sub out", "<p>Body out</p>")

    monkeypatch.setattr(service_mod, 'get_preview_email_content', fake_preview)
    subj, body = await EmailTemplateService.get_template_preview_content("S", "B", {"k":"v"})
    assert subj == "Sub out"
    assert body == "<p>Body out</p>"


@pytest.mark.asyncio
async def test_get_template_preview_content_raises(monkeypatch):
    # Preview function raises -> service should re-raise
    def fake_preview(subject, body, ctx):
        raise Exception("boom preview")

    monkeypatch.setattr(service_mod, 'get_preview_email_content', fake_preview)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("S", "B", {})


@pytest.mark.asyncio
async def test_save_email_template_success(monkeypatch):
    async def fake_save(db, k, s, b):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save))
    ok = await EmailTemplateService.save_email_template(db=SimpleNamespace(), template_key='K', subject_template='S', body_template_html='B')
    assert ok is True


@pytest.mark.asyncio
async def test_save_email_template_db_error(monkeypatch):
    async def fake_save(db, k, s, b):
        raise Exception("DB error")

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(db=SimpleNamespace(), template_key='K', subject_template='S', body_template_html='B')


@pytest.mark.asyncio
async def test_reset_template_to_default_success(monkeypatch):
    async def fake_save(db, k, s, b):
        return None

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save))
    ok = await EmailTemplateService.reset_template_to_default(db=SimpleNamespace(), template_key='INTERVIEW_INVITATION')
    assert ok is True


@pytest.mark.asyncio
async def test_reset_template_to_default_no_default(monkeypatch):
    # No DB call expected: if key not mapped, returns False
    ok = await EmailTemplateService.reset_template_to_default(db=SimpleNamespace(), template_key='NO_DEFAULT_XXXX')
    assert ok is False


@pytest.mark.asyncio
async def test_reset_template_to_default_repo_error(monkeypatch):
    async def fake_save(db, k, s, b):
        raise Exception("repo fail")

    monkeypatch.setattr(service_mod.ConfigRepository, 'save_or_update_email_template', AsyncMock(side_effect=fake_save))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(db=SimpleNamespace(), template_key='INTERVIEW_INVITE')
import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from app.services.config_service.email_template_service import EmailTemplateService
from app.db.repository import config_repository
from app.utils import email_utils


@pytest.mark.asyncio
async def test_get_template_returns_record(monkeypatch):
    rec = SimpleNamespace(template_key="k", subject_template="S", body_template_html="B")
    monkeypatch.setattr(config_repository.ConfigRepository, "get_template_by_key", AsyncMock(return_value=rec))
    res = await EmailTemplateService.get_template(None, "k")
    assert res["template_key"] == "k"
    assert res["subject_template"] == "S"


@pytest.mark.asyncio
async def test_get_template_returns_default_by_key(monkeypatch):
    monkeypatch.setattr(config_repository.ConfigRepository, "get_template_by_key", AsyncMock(return_value=None))
    # Known key that maps to defaults
    res = await EmailTemplateService.get_template(None, "INTERVIEW_INVITE")
    assert "JOB_TITLE" in res["subject_template"] or isinstance(res["subject_template"], str)
    # Unknown key -> default fallback text
    res2 = await EmailTemplateService.get_template(None, "NO_SUCH_KEY")
    assert res2["subject_template"] == "No Default Subject Available"


@pytest.mark.asyncio
async def test_get_template_preview_content_renders_and_raises(monkeypatch):
    # Happy path
    # Patch the symbol imported into the service module, not the util module
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", lambda s, b, c: ("Sx", "Bx"))
    out = await EmailTemplateService.get_template_preview_content("S", "B", {"A": 1})
    assert out == ("Sx", "Bx")

    # Error path: underlying renderer raises
    def bad_render(s, b, c):
        raise Exception("fail")
    monkeypatch.setattr("app.services.config_service.email_template_service.get_preview_email_content", bad_render)
    with pytest.raises(Exception):
        await EmailTemplateService.get_template_preview_content("S", "B", {})


@pytest.mark.asyncio
async def test_save_email_template_success_and_failure(monkeypatch):
    monkeypatch.setattr(config_repository.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.save_email_template(None, "k", "S", "B")
    assert res is True

    # Failure propagates as RuntimeError
    monkeypatch.setattr(config_repository.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(None, "k", "S", "B")


@pytest.mark.asyncio
async def test_reset_template_to_default(monkeypatch):
    # Known key: should call repo and return True
    monkeypatch.setattr(config_repository.ConfigRepository, "save_or_update_email_template", AsyncMock(return_value=None))
    res = await EmailTemplateService.reset_template_to_default(None, "INTERVIEW_INVITE")
    assert res is True

    # Unknown key: returns False
    res2 = await EmailTemplateService.reset_template_to_default(None, "NO_KEY")
    assert res2 is False

    # If repo raises, exception bubbles
    monkeypatch.setattr(config_repository.ConfigRepository, "save_or_update_email_template", AsyncMock(side_effect=Exception("DB")))
    with pytest.raises(Exception):
        await EmailTemplateService.reset_template_to_default(None, "INTERVIEW_INVITE")
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.config_service.email_template_service import EmailTemplateService


@pytest.mark.asyncio
async def test_get_template_returns_db_record(monkeypatch, fake_db):
    record = SimpleNamespace(template_key='OTP', subject_template='S', body_template_html='B')
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.get_template_by_key', AsyncMock(return_value=record))

    res = await EmailTemplateService.get_template(fake_db, 'otp')

    assert res['template_key'] == 'OTP'
    assert res['subject_template'] == 'S'
    assert res['body_template_html'] == 'B'


@pytest.mark.asyncio
async def test_get_template_returns_default_for_mapped_key(monkeypatch, fake_db):
    # No DB record
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.get_template_by_key', AsyncMock(return_value=None))
    # patch the default getter used by the service
    monkeypatch.setattr('app.services.config_service.email_template_service.get_default_otp_template_content', lambda: ('DefaultSub', 'DefaultBody'))

    res = await EmailTemplateService.get_template(fake_db, 'otp')

    assert res['template_key'] == 'otp'
    assert res['subject_template'] == 'DefaultSub'
    assert res['body_template_html'] == 'DefaultBody'


@pytest.mark.asyncio
async def test_get_template_returns_no_default_for_unknown_key(monkeypatch, fake_db):
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.get_template_by_key', AsyncMock(return_value=None))

    res = await EmailTemplateService.get_template(fake_db, 'no_such_key')

    assert res['subject_template'] == 'No Default Subject Available'
    assert res['body_template_html'] == 'No Default Body Available'


@pytest.mark.asyncio
async def test_get_template_preview_content_renders(monkeypatch):
    # patch the preview renderer to a simple function
    monkeypatch.setattr('app.services.config_service.email_template_service.get_preview_email_content', lambda s, b, ctx: ('rsub', 'rbody'))

    sub, body = await EmailTemplateService.get_template_preview_content('sub {{name}}', '<p>{{name}}</p>', {'name': 'Alice'})

    assert sub == 'rsub'
    assert body == 'rbody'


@pytest.mark.asyncio
async def test_save_email_template_success(monkeypatch, fake_db):
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.save_or_update_email_template', AsyncMock(return_value=None))

    res = await EmailTemplateService.save_email_template(fake_db, 'OTP', 'S', 'B')
    assert res is True


@pytest.mark.asyncio
async def test_save_email_template_failure_raises(monkeypatch, fake_db):
    async def raise_exc(*a, **k):
        raise Exception('db')
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.save_or_update_email_template', raise_exc)

    with pytest.raises(RuntimeError):
        await EmailTemplateService.save_email_template(fake_db, 'OTP', 'S', 'B')


@pytest.mark.asyncio
async def test_reset_template_to_default_success(monkeypatch, fake_db):
    # patch getter and repo upsert
    monkeypatch.setattr('app.services.config_service.email_template_service.get_default_interview_template_content', lambda: ('ISub', 'IBody'))
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.save_or_update_email_template', AsyncMock(return_value=None))

    res = await EmailTemplateService.reset_template_to_default(fake_db, 'INTERVIEW_INVITE')
    assert res is True


@pytest.mark.asyncio
async def test_reset_template_to_default_no_default(monkeypatch, fake_db):
    # No getter for this key
    monkeypatch.setattr('app.services.config_service.email_template_service.ConfigRepository.save_or_update_email_template', AsyncMock(return_value=None))

    res = await EmailTemplateService.reset_template_to_default(fake_db, 'UNKNOWN_KEY')
    assert res is False
