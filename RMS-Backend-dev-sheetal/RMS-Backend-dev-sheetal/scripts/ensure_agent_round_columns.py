import asyncio
import os
import sys
from sqlalchemy import text

# Ensure project root is on sys.path so `import app` works when running this script directly.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.db.connection_manager import engine


ALTERS = [
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS interview_mode VARCHAR;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS interview_time_min INTEGER;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS interview_time_max INTEGER;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS interviewer_id UUID;",
]


async def main():
    print("Connecting to DB and ensuring round_config columns...")
    async with engine.begin() as conn:
        for stmt in ALTERS:
            print(f"Executing: {stmt}")
            await conn.execute(text(stmt))
    print("Done. Columns ensured (if DB user had permission and table exists).")


if __name__ == "__main__":
    asyncio.run(main())
