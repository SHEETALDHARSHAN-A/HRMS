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
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_enabled BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_question_mode VARCHAR DEFAULT 'ai';",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_difficulty VARCHAR DEFAULT 'medium';",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_languages JSONB DEFAULT '[]'::jsonb;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS provided_coding_question TEXT;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_test_case_mode VARCHAR DEFAULT 'ai';",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_test_cases JSONB DEFAULT '[]'::jsonb;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS coding_starter_code JSONB DEFAULT '{}'::jsonb;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS mcq_enabled BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS mcq_question_mode VARCHAR DEFAULT 'ai';",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS mcq_difficulty VARCHAR DEFAULT 'medium';",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS mcq_questions JSONB DEFAULT '[]'::jsonb;",
    "ALTER TABLE round_config ADD COLUMN IF NOT EXISTS mcq_passing_score INTEGER DEFAULT 60;",
    "ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS challenge_type VARCHAR DEFAULT 'coding';",
    "ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS submitted_answers JSONB;",
    "ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS test_case_results JSONB;",
    "ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS evaluation_source VARCHAR;",
    "ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS max_score INTEGER;",
    "ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS passed BOOLEAN;",
]


async def main():
    print("Connecting to DB and ensuring round_config columns...")
    async with engine.begin() as conn:
        for stmt in ALTERS:
            print(f"Executing: {stmt}")
            try:
                await conn.execute(text(stmt))
            except Exception as exc:
                print(f"Warning: failed to execute statement: {exc}")
    print("Done. Columns ensured (if DB user had permission and table exists).")


if __name__ == "__main__":
    asyncio.run(main())
