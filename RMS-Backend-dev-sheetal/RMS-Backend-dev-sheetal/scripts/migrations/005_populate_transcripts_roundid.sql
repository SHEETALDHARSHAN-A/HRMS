-- Migration: 005_populate_transcripts_roundid.sql
-- Purpose: Populate existing transcripts.round_id with canonical round_list.id by mapping
-- from transcripts.room_id -> scheduling_interviews.interview_token -> interview_rounds-> round_list.
-- Also add a `round_meta` JSONB column to snapshot the round name/description on each transcript.
-- IMPORTANT: Take a full DB backup before running. This script is idempotent and safe to re-run.

BEGIN;

-- 0) Quick safety: ensure we have a backup table (created by previous migration script if run earlier)
-- If you ran the prior in-place migration, transcripts_backup_before_roundid_migration should exist.
-- If not, create a minimal backup copy now.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = current_schema()
      AND table_name = 'transcripts_backup_before_roundid_migration'
  ) THEN
    EXECUTE 'CREATE TABLE transcripts_backup_before_roundid_migration AS TABLE transcripts WITH NO DATA';
    EXECUTE 'INSERT INTO transcripts_backup_before_roundid_migration SELECT * FROM transcripts';
    RAISE NOTICE 'Created transcripts_backup_before_roundid_migration and copied data.';
  ELSE
    RAISE NOTICE 'Backup table transcripts_backup_before_roundid_migration already exists; skipping.';
  END IF;
END
$$;

-- 1) Add round_meta column to snapshot round details (if not exists)
ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS round_meta jsonb;

-- 2) Populate transcripts.round_id from scheduling_interviews -> interview_rounds -> round_list
-- This relies on transcripts.room_id containing the interview_token (UUID string). We cast room_id to uuid safely.
-- NOTE: casting text->uuid can fail if room_id contains non-UUID strings.
-- Use text-to-text comparison against the interview_token to avoid operator errors.
UPDATE transcripts t
SET round_id = ir.round_id
FROM scheduling_interviews s
JOIN interview_rounds ir ON s.round_id = ir.id
WHERE t.round_id IS NULL
  AND t.room_id IS NOT NULL
  AND s.interview_token IS NOT NULL
  AND s.interview_token::text = t.room_id;

-- 3) Populate round_meta JSONB from round_list for rows where round_id is now set
UPDATE transcripts t
SET round_meta = jsonb_build_object(
  'round_name', rl.round_name,
  'round_description', rl.round_description
)
FROM round_list rl
WHERE t.round_id = rl.id
  AND (t.round_meta IS NULL OR t.round_meta = '{}'::jsonb);

-- 4) Report counts as notices for inspection
DO $$
DECLARE
  total bigint;
  with_round_id bigint;
  with_round_meta bigint;
BEGIN
  SELECT count(*) INTO total FROM transcripts;
  SELECT count(*) INTO with_round_id FROM transcripts WHERE round_id IS NOT NULL;
  SELECT count(*) INTO with_round_meta FROM transcripts WHERE round_meta IS NOT NULL;
  RAISE NOTICE 'transcripts total=% with_round_id=% with_round_meta=%', total, with_round_id, with_round_meta;
END
$$;

COMMIT;

-- Verification queries (run after migration):
-- SELECT t.id, t.room_id, t.round_id, t.round_meta FROM transcripts t ORDER BY t.start_time DESC LIMIT 50;
-- SELECT count(*) FROM transcripts WHERE round_id IS NULL;
-- SELECT * FROM transcripts_unmapped_rows_before_roundid_migration LIMIT 50; -- inspect any previously unmapped rows

-- End of migration
