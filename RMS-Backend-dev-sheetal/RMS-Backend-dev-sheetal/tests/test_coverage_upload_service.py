import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.job_post.upload_jd.upload_job_post import UploadJobPost

@pytest.mark.asyncio
async def test_create_agent_env_error(monkeypatch):
    # Verify error dict returned if creating agent fails
    svc = UploadJobPost(None)
    monkeypatch.setattr("app.services.job_post.upload_jd.upload_job_post.Agent", MagicMock(side_effect=Exception("API Key Invalid")))
    
    res = svc.create_agent()
    assert isinstance(res, dict)
    assert "error" in res
    assert "invalid" in res["error"].lower()

@pytest.mark.asyncio
async def test_extract_docx_exception():
    svc = UploadJobPost(None)
    # Pass invalid bytes to docx parser
    res = svc.extract_text_from_docx(b"not a zip")
    assert res is None

@pytest.mark.asyncio
async def test_extract_job_details_with_text_quota_error(monkeypatch):
    svc = UploadJobPost(None)
    svc.create_agent = lambda: object()
    
    # Mock runner raising quota error
    monkeypatch.setattr("app.services.job_post.upload_jd.upload_job_post.Runner", SimpleNamespace(
        run=AsyncMock(side_effect=Exception("429 insufficient_quota"))
    ))
    
    res = await svc.extract_job_details_with_text("some text")
    assert "limit" in res.get("error", "")

@pytest.mark.asyncio
async def test_pdf_extraction_page_limit_exceeded(monkeypatch):
    svc = UploadJobPost(None)
    
    # Mock convert_from_bytes returning 15 pages
    images = [1] * 15
    monkeypatch.setattr("app.services.job_post.upload_jd.upload_job_post.convert_from_bytes", lambda *a, **k: images)
    
    res = await svc.extract_job_details_with_agent_image(b"fake_pdf")
    assert "exceeds the page limit" in res.get("error", "")