-- Add coding challenge settings to per-round configuration
ALTER TABLE round_config
    ADD COLUMN IF NOT EXISTS coding_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS coding_question_mode TEXT NOT NULL DEFAULT 'ai',
    ADD COLUMN IF NOT EXISTS coding_difficulty TEXT DEFAULT 'medium',
    ADD COLUMN IF NOT EXISTS coding_languages JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS provided_coding_question TEXT;

-- Persist coding submissions and AI evaluation details
CREATE TABLE IF NOT EXISTS coding_submissions (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES job_details(id) ON DELETE CASCADE,
    round_list_id UUID NOT NULL REFERENCES round_list(id) ON DELETE CASCADE,
    interview_token TEXT NOT NULL,
    email TEXT NOT NULL,
    question_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'evaluated',
    ai_score INTEGER,
    ai_feedback TEXT,
    ai_breakdown JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coding_submissions_profile_id ON coding_submissions(profile_id);
CREATE INDEX IF NOT EXISTS idx_coding_submissions_job_id ON coding_submissions(job_id);
CREATE INDEX IF NOT EXISTS idx_coding_submissions_round_list_id ON coding_submissions(round_list_id);
CREATE INDEX IF NOT EXISTS idx_coding_submissions_interview_token ON coding_submissions(interview_token);
