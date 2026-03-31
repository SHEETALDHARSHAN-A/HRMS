-- Migration: normalize interview_duration defaults and backfill
BEGIN;

ALTER TABLE IF EXISTS scheduling_interviews
ALTER COLUMN interview_duration SET DEFAULT 60;

WITH resolved_round AS (
    SELECT
        s.profile_id,
        s.job_id,
        s.round_id,
        s.interview_duration,
        COALESCE(ir.round_id, s.round_id) AS round_list_id
    FROM scheduling_interviews s
    LEFT JOIN interview_rounds ir ON s.round_id = ir.id
), duration_config AS (
    SELECT
        rr.profile_id,
        rr.job_id,
        rr.round_id,
        CASE
            WHEN rc.interview_time_max IS NOT NULL THEN rc.interview_time_max
            WHEN rc.interview_time_min IS NOT NULL THEN rc.interview_time_min
            ELSE NULL
        END AS cfg_duration
    FROM resolved_round rr
    LEFT JOIN round_config rc
        ON rc.job_id = rr.job_id
        AND rc.round_list_id = rr.round_list_id
)
UPDATE scheduling_interviews s
SET interview_duration = LEAST(240, GREATEST(30, COALESCE(dc.cfg_duration, 60)))
FROM duration_config dc
WHERE s.profile_id = dc.profile_id
  AND s.job_id = dc.job_id
  AND s.round_id = dc.round_id
  AND (s.interview_duration IS NULL OR s.interview_duration <= 0 OR s.interview_duration = 20);

COMMIT;
