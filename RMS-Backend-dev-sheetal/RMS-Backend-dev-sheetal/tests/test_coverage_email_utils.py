import pytest
from unittest.mock import AsyncMock, patch
from app.utils.email_utils import _fetch_and_render_saved_template

@pytest.mark.asyncio
async def test_template_alias_matching(fake_db):
    # Tests that "ADMIN_INVITE" key finds "admin_invite_link" if aliased
    from app.services.config_service.email_template_service import ConfigRepository
    
    # Mock the repository to return a record only when asked for "ADMIN_INVITE_LINK"
    async def fake_get(db, key):
        if key == "ADMIN_INVITE_LINK":
            return type("T", (), {"subject_template": "S", "body_template_html": "B"})()
        return None
        
    with patch.object(ConfigRepository, 'get_template_by_key', side_effect=fake_get):
        subj, body = await _fetch_and_render_saved_template(fake_db, "ADMIN_INVITE", {})
        assert subj == "S"