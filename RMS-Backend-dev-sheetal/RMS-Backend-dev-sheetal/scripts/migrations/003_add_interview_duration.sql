-- Migration: add interview_duration to scheduling_interviews
BEGIN;

ALTER TABLE IF EXISTS scheduling_interviews
ADD COLUMN IF NOT EXISTS interview_duration integer NOT NULL DEFAULT 20;

COMMIT;

-- Notes: This adds a non-nullable integer column with default 20 for existing rows.
-- If you use Alembic, convert this into an Alembic revision instead of applying raw SQL.
