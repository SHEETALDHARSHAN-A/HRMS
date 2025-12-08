import pytest
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from io import BytesIO
from docx import Document

from app.services.job_post.upload_jd.upload_job_post import UploadJobPost


class FakeUploadFile:
    def __init__(self, content: bytes, content_type: str = 'application/pdf', filename: str = 'file.pdf'):
        self._content = content
        self.content_type = content_type
        self.filename = filename

    async def read(self):
        return self._content


class DummyRedis:
    def __init__(self, hgetall_return=None):
        self.hgetall = AsyncMock(return_value=hgetall_return)
        self.hset = AsyncMock()


def make_docx_bytes(texts):
    doc = Document()
    for t in texts:
        doc.add_paragraph(t)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()


@pytest.mark.asyncio
async def test_extract_text_from_docx_returns_text():
    # Arrange
    jd = UploadJobPost(redis_store=None)
    b = make_docx_bytes(["Hello world", "Role: Engineer"]) 

    # Act
    text = jd.extract_text_from_docx(b)

    # Assert
    assert text is not None
    assert "Hello world" in text
    assert "Engineer" in text


@pytest.mark.asyncio
async def test_job_details_file_upload_docx_cache_miss_calls_extract_and_stores_cache():
    # Arrange
    doc_bytes = make_docx_bytes(["This is a sample JD", "Skills: Python"])
    file = FakeUploadFile(doc_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename='jd.docx')

    # Redis returns no cache
    redis = DummyRedis(hgetall_return={})

    svc = UploadJobPost(redis_store=redis)

    # Patch extract_text_from_docx to use real method and patch extraction to return a job_details dict
    job_details = {"job_description": "Sample role", "skills": ["Python"]}
    with patch.object(UploadJobPost, 'extract_job_details_with_text', AsyncMock(return_value=job_details)) as mock_extract:
        # Act
        res = await svc.job_details_file_upload(file)

    # Assert
    assert "job_details" in res
    assert res["job_details"]["job_description"] == "Sample role"
    # Ensure cache write attempted
    redis.hset.assert_awaited()


@pytest.mark.asyncio
async def test_job_details_file_upload_cache_hit_returns_cached_value():
    # Arrange
    jd = {"job_description": "cached"}
    cached = {"extracted_content": json.dumps(jd)}
    redis = DummyRedis(hgetall_return=cached)
    svc = UploadJobPost(redis_store=redis)
    file = FakeUploadFile(b"pdfbytes", content_type='application/pdf', filename='file.pdf')

    # Act
    res = await svc.job_details_file_upload(file)

    # Assert
    assert res.get("job_details") == jd


@pytest.mark.asyncio
async def test_job_details_file_upload_unsupported_type_returns_error():
    # Arrange
    redis = DummyRedis(hgetall_return={})
    svc = UploadJobPost(redis_store=redis)
    file = FakeUploadFile(b"text", content_type='text/plain', filename='txt.txt')

    # Act
    res = await svc.job_details_file_upload(file)

    # Assert
    assert "error" in res
    assert "Unsupported file type" in res["error"]


@patch('app.services.job_post.upload_jd.upload_job_post.convert_from_bytes', side_effect=Exception('convert failed'))
@pytest.mark.asyncio
async def test_extract_job_details_with_agent_image_pdf_conversion_failure(mock_convert):
    # Arrange
    redis = DummyRedis(hgetall_return={})
    svc = UploadJobPost(redis_store=redis)
    file_content = b'%PDF-1.4 sample'

    # Act
    res = await svc.extract_job_details_with_agent_image(file_content)

    # Assert
    assert isinstance(res, dict)
    assert "error" in res
    assert "couldn’t read the uploaded PDF" in res["error"] or "couldn’t read" in res["error"].lower()
