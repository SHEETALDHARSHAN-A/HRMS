-- Migration: create transcripts table
BEGIN;

CREATE TABLE IF NOT EXISTS transcripts (
    id uuid PRIMARY KEY,
    profile_id uuid NOT NULL REFERENCES profiles(id),
    job_id uuid NOT NULL REFERENCES job_details(id),
    -- round_id references the canonical round_list table (stores round_list.id)
    round_id uuid REFERENCES round_list(id),
    room_id text,
    conversation jsonb NOT NULL DEFAULT '[]'::jsonb,
    start_time timestamptz NOT NULL DEFAULT now(),
    end_time timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_transcripts_room_id ON transcripts(room_id);

COMMIT;

-- Notes: This creates the `transcripts` table used by the interview agent.
-- Run it with psql or convert to an Alembic revision for production migrations.
