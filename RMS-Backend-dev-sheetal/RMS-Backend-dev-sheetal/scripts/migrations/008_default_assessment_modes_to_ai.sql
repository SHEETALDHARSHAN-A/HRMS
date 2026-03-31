-- Migration: set AI-first defaults for coding/MCQ assessment modes
BEGIN;

ALTER TABLE IF EXISTS round_config
ALTER COLUMN coding_test_case_mode SET DEFAULT 'ai';

ALTER TABLE IF EXISTS round_config
ALTER COLUMN mcq_question_mode SET DEFAULT 'ai';

UPDATE round_config
SET coding_test_case_mode = 'ai'
WHERE coding_test_case_mode IS NULL
   OR btrim(coding_test_case_mode) = ''
   OR (
        lower(btrim(coding_test_case_mode)) = 'provided'
        AND (
            coding_test_cases IS NULL
            OR jsonb_typeof(coding_test_cases) <> 'array'
            OR jsonb_array_length(coding_test_cases) = 0
        )
   );

UPDATE round_config
SET mcq_question_mode = 'ai'
WHERE mcq_question_mode IS NULL
   OR btrim(mcq_question_mode) = ''
   OR (
        lower(btrim(mcq_question_mode)) = 'provided'
        AND (
            mcq_questions IS NULL
            OR jsonb_typeof(mcq_questions) <> 'array'
            OR jsonb_array_length(mcq_questions) = 0
        )
   );

COMMIT;
