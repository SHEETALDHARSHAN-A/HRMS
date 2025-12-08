import pytest

from app.services.job_post.upload_jd.base import BaseUploadJobPost


class ConcreteUpload(BaseUploadJobPost):
    async def job_details_file_upload(self, file):
        # trivial implementation to satisfy the abstract method
        return f"uploaded:{file}"


@pytest.mark.asyncio
async def test_concrete_upload_base_method():
    c = ConcreteUpload()
    res = await c.job_details_file_upload("file1")
    assert res == "uploaded:file1"
