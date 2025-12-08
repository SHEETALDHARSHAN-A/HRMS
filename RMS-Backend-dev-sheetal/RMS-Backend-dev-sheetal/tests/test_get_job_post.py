import pytest

from app.services.job_post.get_job_post import GetJobPost


@pytest.mark.asyncio
async def test_get_job_post_with_sync_reader():
    g = GetJobPost(db_session=None)

    # monkeypatch instance reader to return a plain dict
    class DummyReader:
        def get_job(self, job_id):
            return {"id": job_id}

    g.reader = DummyReader()
    out = await g.fetch_full_job_details("abc-123")
    assert out == {"id": "abc-123"}


@pytest.mark.asyncio
async def test_get_job_post_with_async_reader():
    g = GetJobPost(db_session=None)

    async def coro(job_id):
        return {"id": job_id, "async": True}

    class DummyAsyncReader:
        def get_job(self, job_id):
            return coro(job_id)

    g.reader = DummyAsyncReader()
    out = await g.fetch_full_job_details("xyz-789")
    assert out == {"id": "xyz-789", "async": True}
