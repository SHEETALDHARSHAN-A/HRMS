import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from io import BytesIO
from PIL import Image

from app.services.job_post.upload_jd.upload_job_post import UploadJobPost


@pytest.mark.asyncio
async def test_extract_job_details_with_text_agent_error():
    svc = UploadJobPost(redis_store=None)
    svc.create_agent = lambda: {"error": "no key"}
    res = await svc.extract_job_details_with_text("some text")
    assert isinstance(res, dict)
    assert "error" in res


@pytest.mark.asyncio
async def test_extract_job_details_with_text_parse_failure(monkeypatch):
    svc = UploadJobPost(redis_store=None)
    svc.create_agent = lambda: object()

    runner_result = SimpleNamespace(final_output='not a json')

    async def fake_run(agent, messages):
        return runner_result

    monkeypatch.setattr('app.services.job_post.analyze_jd.analyze_job_post.Runner', object, raising=False)
    # patch the Runner used in upload module
    monkeypatch.setattr('app.services.job_post.upload_jd.upload_job_post.Runner', SimpleNamespace(run=AsyncMock(return_value=runner_result)))

    res = await svc.extract_job_details_with_text("some text")
    assert isinstance(res, dict)
    assert res.get('error') == "Failed to parse extracted job details."


@pytest.mark.asyncio
async def test_extract_job_details_with_agent_image_happy_path(monkeypatch):
    svc = UploadJobPost(redis_store=None)
    # patch create_agent to a dummy object
    svc.create_agent = lambda: object()

    # create a small PIL image
    img = Image.new('RGB', (10, 10), color='white')

    # patch convert_from_bytes to return a list of images
    monkeypatch.setattr('app.services.job_post.upload_jd.upload_job_post.convert_from_bytes', lambda b, poppler_path, fmt, dpi: [img])

    # patch Runner.run to return a final_output containing JSON
    runner_result = SimpleNamespace(final_output='{"job_description": "desc"}')
    monkeypatch.setattr('app.services.job_post.upload_jd.upload_job_post.Runner', SimpleNamespace(run=AsyncMock(return_value=runner_result)))

    res = await svc.extract_job_details_with_agent_image(b'%PDF-1.4 fake')
    assert isinstance(res, dict)
    assert res.get('job_description') == 'desc'
