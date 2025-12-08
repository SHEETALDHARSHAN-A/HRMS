import os
import importlib
import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import app` works when run as a script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def main():
    prev = os.environ.pop("TESTING", None)

    # Reload connection manager to get a declarative Base
    import app.db.connection_manager as cm
    importlib.reload(cm)

    # Use in-memory sqlite async engine
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    TestSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    cm.engine = test_engine
    cm.AsyncSessionLocal = TestSessionLocal

    # Import models and repository modules (avoid reload to prevent duplicate Table registration)
    import app.db.models.job_post_model as job_models
    import app.db.repository.job_post_repository as repo_mod

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(cm.Base.metadata.create_all)

    # Seed data
    async with TestSessionLocal() as session:
        JobDetails = job_models.JobDetails
        SkillList = job_models.SkillList
        LocationList = job_models.LocationList

        job = JobDetails(job_title="Engineer", user_id="00000000-0000-0000-0000-000000000000")
        session.add(job)

        skill = SkillList(skill_name="Python")
        session.add(skill)

        location = LocationList(location="Remote")
        session.add(location)

        await session.commit()

    # Call the repository function
    async with TestSessionLocal() as session:
        res = await repo_mod.get_search_autocomplete_suggestions(session)
        print("RESULT:", res)
        assert "Engineer" in res.get("job_titles", [])

    if prev is not None:
        os.environ["TESTING"] = prev


if __name__ == '__main__':
    try:
        asyncio.get_event_loop().run_until_complete(main())
        print("Integration script succeeded")
        raise SystemExit(0)
    except Exception as e:
        print("Integration script failed:", e)
        raise SystemExit(1)
