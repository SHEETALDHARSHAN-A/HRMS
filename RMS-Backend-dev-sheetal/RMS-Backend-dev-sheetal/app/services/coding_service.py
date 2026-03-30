import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import AppConfig
from app.db.models.agent_config_model import AgentRoundConfig
from app.db.models.coding_submission_model import CodingSubmission
from app.db.models.resume_model import InterviewRounds, Profile
from app.db.models.scheduling_model import Scheduling
from app.db.redis_manager import RedisManager
from app.schemas.coding_request import CodingSubmitRequest

try:
    from groq import AsyncGroq
except Exception:  # pragma: no cover - dependency may be absent in test environments
    AsyncGroq = None


logger = logging.getLogger(__name__)
settings = AppConfig()


SUPPORTED_LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "java",
    "cpp",
    "c",
    "csharp",
    "go",
    "rust",
    "kotlin",
    "swift",
    "php",
    "ruby",
    "scala",
    "r",
    "sql",
    "bash",
    "dart",
]

LANGUAGE_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "cxx": "cpp",
    "gcc": "c",
    "c#": "csharp",
    "dotnet": "csharp",
    "golang": "go",
    "postgres": "sql",
    "shell": "bash",
    "sh": "bash",
}

DEFAULT_STARTER_SNIPPETS = {
    "python": "def solve(input_data):\n    # Write your solution here\n    return None\n",
    "javascript": "function solve(inputData) {\n  // Write your solution here\n  return null;\n}\n",
    "typescript": "function solve(inputData: unknown): unknown {\n  // Write your solution here\n  return null;\n}\n",
    "java": "class Solution {\n    public static Object solve(Object inputData) {\n        // Write your solution here\n        return null;\n    }\n}\n",
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n",
    "go": "package main\n\nfunc solve(inputData any) any {\n    // Write your solution here\n    return nil\n}\n",
}


class CodingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_question(self, token: str, email: str) -> Dict[str, Any]:
        context = await self._resolve_candidate_context(token=token, email=email)
        public_payload, full_payload = await self._build_assessment_payload(context)
        await self._store_assessment_payload(token=token, email=email, payload=full_payload)
        return public_payload

    async def submit_solution(self, request: CodingSubmitRequest) -> Dict[str, Any]:
        email = str(request.email)
        context = await self._resolve_candidate_context(token=request.token, email=email)
        security_validation = self._enforce_submission_security(request=request, context=context)

        stored_payload = await self._load_assessment_payload(token=request.token, email=email)
        question_payload = stored_payload or request.question
        if not question_payload:
            _, question_payload = await self._build_assessment_payload(context)

        requested_challenge_type = (request.challengeType or "").strip().lower()
        if requested_challenge_type not in {"coding", "mcq"}:
            requested_challenge_type = ""

        challenge_type = (
            requested_challenge_type
            or str(question_payload.get("challengeType") or "").strip().lower()
            or context.get("challenge_type", "coding")
        )
        if challenge_type not in {"coding", "mcq"}:
            challenge_type = "coding"

        submitted_answers: Optional[List[Dict[str, str]]] = None
        submission_language = "mcq"
        submission_code = ""

        if challenge_type == "mcq":
            submitted_answers = [
                {"questionId": item.questionId, "selectedOptionId": item.selectedOptionId}
                for item in (request.mcqAnswers or [])
            ]
            evaluation = self._evaluate_mcq_submission(
                question_payload=question_payload,
                mcq_answers=submitted_answers,
            )
        else:
            submission_code = (request.code or "").strip()
            if not submission_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Code is required for coding submissions",
                )

            allowed_languages = self._normalize_languages(getattr(context["config"], "coding_languages", None))
            requested_language = self._canonical_language(request.language or allowed_languages[0])
            if requested_language not in allowed_languages:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported language '{requested_language}'. Allowed: {', '.join(allowed_languages)}",
                )

            submission_language = requested_language
            evaluation = await self._evaluate_coding_submission(
                question_payload=question_payload,
                code=submission_code,
                language=submission_language,
            )

        submission = CodingSubmission(
            id=uuid.uuid4(),
            profile_id=context["profile_id"],
            job_id=context["job_id"],
            round_list_id=context["round_list_id"],
            interview_token=request.token,
            email=email,
            question_payload=question_payload,
            challenge_type=challenge_type,
            language=submission_language,
            code=submission_code,
            submitted_answers=submitted_answers,
            test_case_results=evaluation.get("testCaseResults"),
            status="evaluated",
            evaluation_source=evaluation.get("evaluationSource"),
            max_score=evaluation.get("maxScore"),
            passed=evaluation.get("passed"),
            ai_score=evaluation.get("score"),
            ai_feedback=evaluation.get("feedback"),
            ai_breakdown=evaluation.get("breakdown"),
        )

        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)

        return {
            "submissionId": str(submission.id),
            "challengeType": submission.challenge_type,
            "score": submission.ai_score,
            "feedback": submission.ai_feedback,
            "breakdown": submission.ai_breakdown,
            "testCaseResults": submission.test_case_results,
            "passed": submission.passed,
            "maxScore": submission.max_score,
            "evaluationSource": submission.evaluation_source,
            "language": submission.language,
            "status": submission.status,
            "question": submission.question_payload,
            "securityValidation": security_validation,
        }

    async def get_submission(self, submission_id: str, token: str, email: str) -> Dict[str, Any]:
        context = await self._resolve_candidate_context(token=token, email=email)

        try:
            submission_uuid = uuid.UUID(submission_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission ID")

        stmt = (
            select(CodingSubmission)
            .where(CodingSubmission.id == submission_uuid)
            .where(CodingSubmission.profile_id == context["profile_id"])
            .where(CodingSubmission.interview_token == token)
        )
        result = await self.db.execute(stmt)
        submission = result.scalar_one_or_none()

        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        return {
            "submissionId": str(submission.id),
            "challengeType": submission.challenge_type,
            "score": submission.ai_score,
            "feedback": submission.ai_feedback,
            "breakdown": submission.ai_breakdown,
            "testCaseResults": submission.test_case_results,
            "passed": submission.passed,
            "maxScore": submission.max_score,
            "evaluationSource": submission.evaluation_source,
            "language": submission.language,
            "status": submission.status,
            "question": submission.question_payload,
            "createdAt": submission.created_at.isoformat() if submission.created_at else None,
        }

    async def _resolve_candidate_context(self, token: str, email: str) -> Dict[str, Any]:
        stmt = (
            select(Scheduling, Profile)
            .join(Profile, Scheduling.profile_id == Profile.id)
            .where(cast(Scheduling.interview_token, String) == str(token))
            .where(Profile.email == email)
        )

        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview context not found for provided token and email",
            )

        schedule, profile = row
        round_list_id = await self._resolve_round_list_id(schedule)
        if round_list_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unable to resolve interview round for assessment context",
            )

        config_stmt = (
            select(AgentRoundConfig)
            .where(AgentRoundConfig.job_id == schedule.job_id)
            .where(AgentRoundConfig.round_list_id == round_list_id)
        )
        config_result = await self.db.execute(config_stmt)
        config = config_result.scalar_one_or_none()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Round configuration not found",
            )

        interview_mode = (getattr(config, "interview_mode", "") or "").strip().lower()
        coding_enabled = bool(getattr(config, "coding_enabled", False)) or interview_mode in {"coding", "code"}
        mcq_enabled = bool(getattr(config, "mcq_enabled", False)) or interview_mode in {
            "mcq",
            "quiz",
            "aptitude",
            "apti",
            "apti_screening",
        }
        if not coding_enabled and not mcq_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Neither coding nor MCQ challenge is enabled for this interview round",
            )

        challenge_type = self._detect_challenge_type(config)
        self._validate_schedule_window(schedule=schedule, challenge_type=challenge_type)
        runtime_policy = await self._load_runtime_policy(token=token)

        return {
            "schedule": schedule,
            "profile": profile,
            "config": config,
            "profile_id": schedule.profile_id,
            "job_id": schedule.job_id,
            "round_list_id": round_list_id,
            "challenge_type": challenge_type,
            "runtime_policy": runtime_policy,
        }

    def _validate_schedule_window(self, schedule: Scheduling, challenge_type: str) -> None:
        scheduled_at = getattr(schedule, "scheduled_datetime", None)
        expires_at = getattr(schedule, "expired_at", None)
        now_utc = datetime.now(timezone.utc)

        if scheduled_at is not None:
            if getattr(scheduled_at, "tzinfo", None) is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            if now_utc < scheduled_at:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Assessment has not started yet. Please join at the scheduled start time.",
                )

        if expires_at is not None:
            if getattr(expires_at, "tzinfo", None) is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now_utc > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Assessment window has ended. Please contact the recruiter for rescheduling.",
                )

    def _enforce_submission_security(self, request: CodingSubmitRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        policy = context.get("runtime_policy") if isinstance(context.get("runtime_policy"), dict) else {}
        secure_required = bool(policy.get("secureBrowserRequired", False))
        proctor_required = bool(policy.get("proctoringRequired", False))

        if not secure_required and not proctor_required:
            return {
                "required": False,
                "validated": False,
                "reason": "runtime_policy_not_enforced",
            }

        secure_meta = request.secureBrowserMeta or {}
        proctor_signals = request.proctoringSignals or {}

        if secure_required and not bool(secure_meta.get("isSecureBrowser", False)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Secure browser mode is required for this assessment round.",
            )

        if proctor_required:
            if not isinstance(proctor_signals, dict) or not proctor_signals:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Proctoring telemetry is required for this assessment round.",
                )

            head_alerts = proctor_signals.get("headMovementAlerts")
            eye_alerts = proctor_signals.get("eyeAwayAlerts")
            if head_alerts is not None:
                try:
                    if int(head_alerts) > 20:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Head-movement risk threshold exceeded during assessment.",
                        )
                except HTTPException:
                    raise
                except Exception:
                    pass

            if eye_alerts is not None:
                try:
                    if int(eye_alerts) > 20:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Eye-focus risk threshold exceeded during assessment.",
                        )
                except HTTPException:
                    raise
                except Exception:
                    pass

        return {
            "required": True,
            "validated": True,
            "secureBrowserRequired": secure_required,
            "proctoringRequired": proctor_required,
        }

    async def _load_runtime_policy(self, token: str) -> Dict[str, Any]:
        try:
            redis_client = RedisManager.get_client()
            raw = await redis_client.get(f"interview_runtime_policy:{str(token).strip()}")
            if not raw:
                return {}
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    async def _resolve_round_list_id(self, schedule: Scheduling) -> Optional[Any]:
        stmt = select(InterviewRounds).where(InterviewRounds.id == schedule.round_id)
        result = await self.db.execute(stmt)
        interview_round = result.scalar_one_or_none()
        if interview_round is not None:
            return interview_round.round_id

        fallback_stmt = (
            select(InterviewRounds)
            .where(InterviewRounds.job_id == schedule.job_id)
            .where(InterviewRounds.profile_id == schedule.profile_id)
            .where(InterviewRounds.round_id == schedule.round_id)
            .order_by(InterviewRounds.id.desc())
        )
        fallback_result = await self.db.execute(fallback_stmt)
        fallback_interview_round = fallback_result.scalars().first()
        if fallback_interview_round is not None:
            return fallback_interview_round.round_id

        return schedule.round_id

    async def _build_assessment_payload(self, context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        config = context["config"]
        challenge_type = context.get("challenge_type", "coding")

        if challenge_type == "mcq":
            full_payload = await self._build_mcq_question(config=config)
        else:
            full_payload = await self._build_coding_question(config=config)

        full_payload["challengeType"] = challenge_type
        full_payload["roundListId"] = str(context["round_list_id"])
        full_payload["jobId"] = str(context["job_id"])

        return self._to_public_payload(full_payload), full_payload

    async def _build_coding_question(self, config: AgentRoundConfig) -> Dict[str, Any]:
        question_mode = (getattr(config, "coding_question_mode", "ai") or "ai").lower()
        difficulty = (getattr(config, "coding_difficulty", "medium") or "medium").lower()
        languages = self._normalize_languages(getattr(config, "coding_languages", None))
        provided_question = (getattr(config, "provided_coding_question", None) or "").strip()

        if question_mode == "provided" and provided_question:
            question_payload = {
                "source": "provided",
                "title": f"{getattr(config, 'round_name', 'Coding Round')} Challenge",
                "problem": provided_question,
                "constraints": [
                    "Write clean, readable code.",
                    "Handle invalid and edge inputs safely.",
                ],
                "hints": [],
            }
        else:
            question_payload = await self._generate_ai_question(config=config, difficulty=difficulty, languages=languages)

        test_case_mode = (getattr(config, "coding_test_case_mode", "provided") or "provided").lower()
        configured_test_cases = self._normalize_test_cases(getattr(config, "coding_test_cases", None))

        if test_case_mode == "provided" and configured_test_cases:
            test_cases = configured_test_cases
        else:
            generated = await self._generate_ai_test_cases(
                question_payload=question_payload,
                language=languages[0],
                difficulty=difficulty,
            )
            test_cases = generated or configured_test_cases or self._default_test_cases()

        starter_code = self._build_starter_code(
            languages=languages,
            configured_starter=getattr(config, "coding_starter_code", None),
        )

        question_payload["difficulty"] = difficulty
        question_payload["languages"] = languages
        question_payload["questionMode"] = question_mode
        question_payload["testCaseMode"] = test_case_mode
        question_payload["testCases"] = test_cases
        question_payload["starterCode"] = starter_code
        return question_payload

    async def _build_mcq_question(self, config: AgentRoundConfig) -> Dict[str, Any]:
        question_mode = (getattr(config, "mcq_question_mode", "provided") or "provided").lower()
        difficulty = (getattr(config, "mcq_difficulty", "medium") or "medium").lower()
        configured_questions = self._normalize_mcq_questions(getattr(config, "mcq_questions", None))

        if question_mode == "provided" and configured_questions:
            questions = configured_questions
            source = "provided"
        else:
            generated_questions = await self._generate_ai_mcq_questions(config=config, difficulty=difficulty)
            questions = generated_questions or configured_questions or self._fallback_mcq_questions()
            source = "ai" if generated_questions else "provided"

        passing_score = self._coerce_score(getattr(config, "mcq_passing_score", 60), default=60)

        return {
            "source": source,
            "title": f"{getattr(config, 'round_name', 'MCQ Round')} MCQ Challenge",
            "instructions": "Choose the best answer for each question.",
            "difficulty": difficulty,
            "questionMode": question_mode,
            "questions": questions,
            "passingScore": passing_score,
        }

    async def _generate_ai_question(self, config: AgentRoundConfig, difficulty: str, languages: List[str]) -> Dict[str, Any]:
        skills = getattr(config, "key_skills", None) or []
        focus = getattr(config, "round_focus", None) or "data structures and problem solving"
        primary_skill = skills[0] if skills else "problem solving"

        fallback_question = {
            "source": "ai",
            "title": f"{primary_skill.title()} Challenge",
            "problem": (
                f"Build a function in {languages[0]} to solve a {difficulty} level {primary_skill} task. "
                "Your function should handle edge cases and include a brief explanation of your approach."
            ),
            "constraints": [
                "Time complexity should be explained.",
                "Handle invalid or empty input safely.",
            ],
            "hints": [
                "Start with a brute-force approach, then optimize.",
                "Think through edge cases before coding.",
            ],
        }

        if not self._can_call_groq():
            return fallback_question

        client = AsyncGroq(api_key=settings.effective_groq_api_key)
        prompt = f"""
Generate one coding interview question as strict JSON with keys:
- title (string)
- problem (string)
- constraints (array of strings)
- hints (array of strings)

Context:
- Round focus: {focus}
- Priority skills: {', '.join(skills) if skills else 'general coding'}
- Difficulty: {difficulty}
- Allowed languages: {', '.join(languages)}

Return only valid JSON.
"""

        try:
            completion = await client.chat.completions.create(
                model=settings.effective_groq_model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You generate structured coding interview prompts."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or ""
            parsed = self._extract_json(content)
            if not parsed:
                return fallback_question
            parsed["source"] = "ai"
            parsed.setdefault("constraints", fallback_question["constraints"])
            parsed.setdefault("hints", fallback_question["hints"])
            return parsed
        except Exception as exc:
            logger.warning("Groq question generation failed, using fallback question: %s", exc)
            return fallback_question

    async def _generate_ai_test_cases(
        self,
        question_payload: Dict[str, Any],
        language: str,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        if not self._can_call_groq():
            return []

        client = AsyncGroq(api_key=settings.effective_groq_api_key)
        prompt = f"""
Generate 5 coding test cases for the following question.
Return strict JSON with one key `testCases`.

Each test case object must include:
- input (string)
- expectedOutput (string)
- isHidden (boolean)
- weight (integer between 1 and 5)

Question:
{json.dumps(question_payload, ensure_ascii=True)}

Language: {language}
Difficulty: {difficulty}

Constraints:
- Include at least 2 hidden test cases.
- Include both normal and edge cases.
"""

        try:
            completion = await client.chat.completions.create(
                model=settings.effective_groq_model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You generate reliable coding test cases."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or ""
            parsed = self._extract_json(content)
            if not parsed:
                return []
            raw_cases = parsed.get("testCases") if isinstance(parsed.get("testCases"), list) else []
            return self._normalize_test_cases(raw_cases)
        except Exception as exc:
            logger.warning("Groq test-case generation failed: %s", exc)
            return []

    async def _generate_ai_mcq_questions(self, config: AgentRoundConfig, difficulty: str) -> List[Dict[str, Any]]:
        if not self._can_call_groq():
            return []

        skills = getattr(config, "key_skills", None) or []
        focus = getattr(config, "round_focus", None) or "core fundamentals"
        client = AsyncGroq(api_key=settings.effective_groq_api_key)

        prompt = f"""
Generate 5 MCQ interview questions as strict JSON object with key `questions`.

Each item in questions must include:
- question (string)
- options (array of exactly 4 option strings)
- answer (one option string that is correct)
- explanation (string)

Context:
- Round focus: {focus}
- Skills: {', '.join(skills) if skills else 'general aptitude and technical basics'}
- Difficulty: {difficulty}
"""

        try:
            completion = await client.chat.completions.create(
                model=settings.effective_groq_model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You generate objective interview MCQ question sets."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or ""
            parsed = self._extract_json(content)
            if not parsed:
                return []
            return self._normalize_mcq_questions(parsed.get("questions"))
        except Exception as exc:
            logger.warning("Groq MCQ generation failed: %s", exc)
            return []

    async def _evaluate_coding_submission(self, question_payload: Dict[str, Any], code: str, language: str) -> Dict[str, Any]:
        normalized_test_cases = self._normalize_test_cases(question_payload.get("testCases"))
        test_case_eval = await self._evaluate_test_cases(
            question_payload=question_payload,
            code=code,
            language=language,
            test_cases=normalized_test_cases,
        )
        quality_eval = await self._evaluate_quality(question_payload=question_payload, code=code, language=language)

        test_case_score = test_case_eval.get("score")
        if isinstance(test_case_score, int):
            final_score = int(round((0.7 * test_case_score) + (0.3 * quality_eval["score"])))
            source = f"{test_case_eval['source']}+{quality_eval['source']}"
            feedback = (
                f"Test-case score: {test_case_score}/100. "
                f"Quality score: {quality_eval['score']}/100. "
                f"{test_case_eval.get('summary', '')} {quality_eval['feedback']}"
            ).strip()
        else:
            final_score = quality_eval["score"]
            source = quality_eval["source"]
            feedback = quality_eval["feedback"]

        strengths = list(
            dict.fromkeys(
                (quality_eval["breakdown"].get("strengths") or []) + (test_case_eval.get("strengths") or [])
            )
        )
        improvements = list(
            dict.fromkeys(
                (quality_eval["breakdown"].get("improvements") or []) + (test_case_eval.get("improvements") or [])
            )
        )

        breakdown = {
            "correctness": test_case_score
            if isinstance(test_case_score, int)
            else quality_eval["breakdown"].get("correctness", quality_eval["score"]),
            "clarity": quality_eval["breakdown"].get("clarity", quality_eval["score"]),
            "robustness": quality_eval["breakdown"].get("robustness", max(0, quality_eval["score"] - 5)),
            "strengths": strengths,
            "improvements": improvements,
            "testCasePassRate": test_case_score,
        }

        final_score = max(0, min(100, final_score))
        return {
            "score": final_score,
            "feedback": feedback,
            "breakdown": breakdown,
            "testCaseResults": test_case_eval.get("results"),
            "evaluationSource": source,
            "maxScore": 100,
            "passed": final_score >= 60,
        }

    async def _evaluate_test_cases(
        self,
        question_payload: Dict[str, Any],
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not test_cases:
            return {
                "score": None,
                "results": [],
                "summary": "No test cases configured for this challenge.",
                "source": "no-test-cases",
                "strengths": [],
                "improvements": ["Add preconfigured test cases for objective evaluation."],
            }

        ai_result = await self._evaluate_test_cases_with_ai(
            question_payload=question_payload,
            code=code,
            language=language,
            test_cases=test_cases,
        )
        if ai_result:
            return ai_result

        return self._evaluate_test_cases_heuristic(code=code, language=language, test_cases=test_cases)

    async def _evaluate_test_cases_with_ai(
        self,
        question_payload: Dict[str, Any],
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self._can_call_groq():
            return None

        client = AsyncGroq(api_key=settings.effective_groq_api_key)
        prompt = f"""
Evaluate whether this code passes each test case. Return strict JSON object with:
- results: array of {{id, passed, actualOutput, notes}}
- summary: short string summary

Question:
{json.dumps(question_payload, ensure_ascii=True)}

Language: {language}
Code:
{code}

Test cases:
{json.dumps(test_cases, ensure_ascii=True)}
"""

        try:
            completion = await client.chat.completions.create(
                model=settings.effective_groq_model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a strict code evaluator. Be objective and concise."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or ""
            parsed = self._extract_json(content)
            if not parsed:
                return None

            raw_results = parsed.get("results")
            if not isinstance(raw_results, list):
                return None

            scored = self._score_test_case_results(test_cases=test_cases, raw_results=raw_results)
            scored["summary"] = parsed.get("summary") if isinstance(parsed.get("summary"), str) else scored["summary"]
            scored["source"] = "ai-test-cases"

            if scored["score"] >= 80:
                scored["strengths"] = ["Passes most configured test cases."]
                scored["improvements"] = []
            else:
                scored["strengths"] = []
                scored["improvements"] = ["Address failing test cases and validate edge conditions."]
            return scored
        except Exception as exc:
            logger.warning("AI test-case evaluation failed: %s", exc)
            return None

    def _evaluate_test_cases_heuristic(self, code: str, language: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        stripped = (code or "").strip()
        confidence = 0.15

        if len(stripped) >= 120:
            confidence += 0.25
        if re.search(r"\b(if|for|while|switch|case|match)\b", stripped):
            confidence += 0.2
        if re.search(r"\b(return)\b", stripped):
            confidence += 0.2
        if re.search(r"\b(def |function |class |fn |public static)\b", stripped):
            confidence += 0.1
        if "TODO" not in stripped and "pass" not in stripped:
            confidence += 0.1
        if re.search(r"(#|//)", stripped):
            confidence += 0.05

        confidence = max(0.05, min(0.95, confidence))

        raw_results: List[Dict[str, Any]] = []
        for idx, case in enumerate(test_cases):
            threshold = 0.3 + (idx * 0.08) + (0.12 if case.get("isHidden") else 0.0)
            threshold = min(0.9, threshold)
            passed = confidence >= threshold
            raw_results.append(
                {
                    "id": case["id"],
                    "passed": passed,
                    "actualOutput": "Heuristic static analysis (runtime execution not available).",
                    "notes": "Confidence-based estimate.",
                }
            )

        scored = self._score_test_case_results(test_cases=test_cases, raw_results=raw_results)
        scored["source"] = "heuristic-test-cases"

        if scored["score"] >= 70:
            scored["strengths"] = [f"Estimated {scored['score']}% test-case pass rate for {language}."]
            scored["improvements"] = []
        else:
            scored["strengths"] = []
            scored["improvements"] = ["Implementation likely misses one or more edge scenarios from configured test cases."]

        return scored

    def _score_test_case_results(self, test_cases: List[Dict[str, Any]], raw_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        result_map: Dict[str, Dict[str, Any]] = {}
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            case_id = str(item.get("id") or "").strip()
            if not case_id:
                continue
            result_map[case_id] = item

        total_weight = sum(int(case.get("weight", 1)) for case in test_cases)
        total_weight = max(1, total_weight)

        earned_weight = 0
        passed_count = 0
        results: List[Dict[str, Any]] = []
        for case in test_cases:
            case_id = case["id"]
            matched = result_map.get(case_id, {})
            passed = bool(matched.get("passed"))
            weight = int(case.get("weight", 1))
            if passed:
                earned_weight += weight
                passed_count += 1

            results.append(
                {
                    "id": case_id,
                    "input": case.get("input"),
                    "expectedOutput": case.get("expectedOutput"),
                    "isHidden": bool(case.get("isHidden", False)),
                    "weight": weight,
                    "passed": passed,
                    "actualOutput": matched.get("actualOutput"),
                    "notes": matched.get("notes"),
                }
            )

        score = int(round((earned_weight / total_weight) * 100))
        summary = f"{passed_count}/{len(test_cases)} test cases passed."
        return {
            "score": score,
            "results": results,
            "summary": summary,
        }

    async def _evaluate_quality(self, question_payload: Dict[str, Any], code: str, language: str) -> Dict[str, Any]:
        fallback = self._heuristic_evaluation(code=code, language=language)

        if not self._can_call_groq():
            return {
                **fallback,
                "source": "heuristic-quality",
            }

        client = AsyncGroq(api_key=settings.effective_groq_api_key)
        prompt = f"""
Evaluate this coding submission and return strict JSON with keys:
- score (integer 0-100)
- feedback (string)
- breakdown (object with correctness, clarity, robustness each 0-100 and strengths/improvements arrays)

Question:
{json.dumps(question_payload, ensure_ascii=True)}

Language: {language}
Code:
{code}

Return only valid JSON.
"""

        try:
            completion = await client.chat.completions.create(
                model=settings.effective_groq_model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a strict technical interviewer grading code."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or ""
            parsed = self._extract_json(content)
            if not parsed:
                return {
                    **fallback,
                    "source": "heuristic-quality",
                }

            score = self._coerce_score(parsed.get("score"), default=fallback["score"])
            feedback = parsed.get("feedback") if isinstance(parsed.get("feedback"), str) else fallback["feedback"]
            raw_breakdown = parsed.get("breakdown") if isinstance(parsed.get("breakdown"), dict) else fallback["breakdown"]
            breakdown = {
                "correctness": self._coerce_score(raw_breakdown.get("correctness"), default=min(100, score + 5)),
                "clarity": self._coerce_score(raw_breakdown.get("clarity"), default=score),
                "robustness": self._coerce_score(raw_breakdown.get("robustness"), default=max(0, score - 5)),
                "strengths": [str(item) for item in (raw_breakdown.get("strengths") or [])],
                "improvements": [str(item) for item in (raw_breakdown.get("improvements") or [])],
            }

            return {
                "score": score,
                "feedback": feedback,
                "breakdown": breakdown,
                "source": "ai-quality",
            }
        except Exception as exc:
            logger.warning("Groq quality evaluation failed, using heuristic evaluation: %s", exc)
            return {
                **fallback,
                "source": "heuristic-quality",
            }

    def _evaluate_mcq_submission(self, question_payload: Dict[str, Any], mcq_answers: List[Dict[str, str]]) -> Dict[str, Any]:
        questions = self._normalize_mcq_questions(question_payload.get("questions"))
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCQ question set is missing or invalid",
            )

        answer_map: Dict[str, str] = {}
        for answer in mcq_answers:
            question_id = str(answer.get("questionId") or "").strip()
            option_id = str(answer.get("selectedOptionId") or "").strip()
            if question_id and option_id:
                answer_map[question_id] = option_id

        results: List[Dict[str, Any]] = []
        correct_count = 0
        for question in questions:
            question_id = question["id"]
            correct_option_id = str(question.get("correctOptionId") or "").strip()
            selected_option_id = answer_map.get(question_id)
            is_correct = bool(correct_option_id and selected_option_id == correct_option_id)
            if is_correct:
                correct_count += 1

            results.append(
                {
                    "questionId": question_id,
                    "selectedOptionId": selected_option_id,
                    "correctOptionId": correct_option_id,
                    "isCorrect": is_correct,
                }
            )

        total_questions = len(questions)
        score = int(round((correct_count / max(1, total_questions)) * 100))
        passing_score = self._coerce_score(question_payload.get("passingScore"), default=60)
        passed = score >= passing_score

        feedback = (
            f"You answered {correct_count} out of {total_questions} correctly. "
            f"Score: {score}/100. Passing threshold: {passing_score}/100."
        )

        strengths = ["Strong conceptual accuracy in objective questions."] if score >= 80 else []
        improvements = [] if score >= 80 else ["Revisit missed topics and retry similar MCQ patterns."]

        return {
            "score": score,
            "feedback": feedback,
            "breakdown": {
                "correctness": score,
                "clarity": score,
                "robustness": score,
                "strengths": strengths,
                "improvements": improvements,
                "totalQuestions": total_questions,
                "correctAnswers": correct_count,
            },
            "testCaseResults": results,
            "evaluationSource": "objective-mcq",
            "maxScore": 100,
            "passed": passed,
        }

    def _heuristic_evaluation(self, code: str, language: str) -> Dict[str, Any]:
        stripped = (code or "").strip()
        score = 15
        strengths: List[str] = []
        improvements: List[str] = []

        if len(stripped) >= 80:
            score += 20
            strengths.append("Provides a reasonably complete implementation.")
        else:
            improvements.append("Implementation appears short; add full handling and edge cases.")

        if re.search(r"\b(if|for|while|switch|case)\b", stripped):
            score += 20
            strengths.append("Uses control flow logic appropriately.")
        else:
            improvements.append("Add conditional or iterative logic where required by the problem.")

        if re.search(r"\b(return)\b", stripped):
            score += 20
            strengths.append("Returns computed output explicitly.")
        else:
            improvements.append("Ensure your function returns the required result.")

        if re.search(r"\b(def |function |class )", stripped):
            score += 15
            strengths.append("Uses structured function/class definition.")
        else:
            improvements.append("Wrap logic in a clear function signature.")

        if "TODO" not in stripped and "pass" not in stripped:
            score += 10
            strengths.append("Submission avoids placeholder markers.")
        else:
            improvements.append("Replace TODO/pass placeholders with complete logic.")

        if len(improvements) == 0:
            improvements.append("Add small comments explaining key decisions.")

        score = max(0, min(100, score))
        feedback = (
            f"Estimated score {score}/100 for {language}. "
            "This MVP evaluation is AI-assisted and should be reviewed alongside interview discussion."
        )

        return {
            "score": score,
            "feedback": feedback,
            "breakdown": {
                "correctness": min(100, score + 5),
                "clarity": min(100, score),
                "robustness": max(0, score - 5),
                "strengths": strengths,
                "improvements": improvements,
            },
        }

    def _normalize_languages(self, raw_languages: Optional[Any]) -> List[str]:
        if isinstance(raw_languages, list):
            cleaned: List[str] = []
            for lang in raw_languages:
                canonical = self._canonical_language(str(lang))
                if canonical in SUPPORTED_LANGUAGES and canonical not in cleaned:
                    cleaned.append(canonical)
            if cleaned:
                return cleaned
        return ["python", "javascript", "java", "cpp", "go"]

    @staticmethod
    def _canonical_language(raw_language: str) -> str:
        normalized = (raw_language or "").strip().lower()
        return LANGUAGE_ALIASES.get(normalized, normalized)

    def _build_starter_code(self, languages: List[str], configured_starter: Optional[Any]) -> Dict[str, str]:
        starter: Dict[str, str] = {}
        if isinstance(configured_starter, dict):
            for key, value in configured_starter.items():
                if not isinstance(value, str):
                    continue
                canonical = self._canonical_language(str(key))
                if canonical in SUPPORTED_LANGUAGES:
                    starter[canonical] = value

        for lang in languages:
            if lang not in starter:
                starter[lang] = DEFAULT_STARTER_SNIPPETS.get(lang, "# Write your solution here\n")
        return starter

    def _normalize_test_cases(self, raw_test_cases: Optional[Any]) -> List[Dict[str, Any]]:
        if not isinstance(raw_test_cases, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for idx, raw_case in enumerate(raw_test_cases):
            if not isinstance(raw_case, dict):
                continue

            case_input = raw_case.get("input", raw_case.get("stdin", raw_case.get("args", "")))
            expected_output = raw_case.get("expectedOutput", raw_case.get("expected_output", raw_case.get("output", "")))

            weight_raw = raw_case.get("weight", 1)
            try:
                weight = int(weight_raw)
            except Exception:
                weight = 1
            weight = max(1, min(10, weight))

            normalized.append(
                {
                    "id": str(raw_case.get("id") or f"tc_{idx + 1}"),
                    "input": str(case_input or ""),
                    "expectedOutput": str(expected_output or ""),
                    "isHidden": bool(raw_case.get("isHidden", raw_case.get("hidden", False))),
                    "weight": weight,
                }
            )
        return normalized

    def _normalize_mcq_questions(self, raw_questions: Optional[Any]) -> List[Dict[str, Any]]:
        if not isinstance(raw_questions, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for idx, raw_question in enumerate(raw_questions):
            if not isinstance(raw_question, dict):
                continue

            question_text = raw_question.get("question", raw_question.get("prompt", raw_question.get("title", "")))
            if not isinstance(question_text, str) or not question_text.strip():
                continue

            raw_options = raw_question.get("options", [])
            if not isinstance(raw_options, list):
                continue

            options: List[Dict[str, str]] = []
            for option_index, raw_option in enumerate(raw_options):
                if isinstance(raw_option, dict):
                    option_text = raw_option.get("text", raw_option.get("label", raw_option.get("option", "")))
                    option_id = str(raw_option.get("id") or f"q{idx + 1}_opt{option_index + 1}")
                else:
                    option_text = str(raw_option)
                    option_id = f"q{idx + 1}_opt{option_index + 1}"

                if not option_text or not str(option_text).strip():
                    continue
                options.append({"id": option_id, "text": str(option_text).strip()})

            if len(options) < 2:
                continue

            correct_option_id = raw_question.get("correctOptionId", raw_question.get("correct_option_id", raw_question.get("answerId")))
            if correct_option_id is None:
                answer_text = raw_question.get("answer")
                if answer_text is not None:
                    answer_text_l = str(answer_text).strip().lower()
                    for option in options:
                        if option["id"].strip().lower() == answer_text_l or option["text"].strip().lower() == answer_text_l:
                            correct_option_id = option["id"]
                            break

            if correct_option_id is not None:
                correct_option_id = str(correct_option_id)
                if not any(option["id"] == correct_option_id for option in options):
                    correct_option_id = None

            normalized.append(
                {
                    "id": str(raw_question.get("id") or f"q_{idx + 1}"),
                    "question": question_text.strip(),
                    "options": options,
                    "correctOptionId": correct_option_id,
                    "explanation": str(raw_question.get("explanation") or "").strip() or None,
                }
            )
        return normalized

    def _fallback_mcq_questions(self) -> List[Dict[str, Any]]:
        return self._normalize_mcq_questions(
            [
                {
                    "question": "Which data structure provides average O(1) key lookup?",
                    "options": ["Array", "Hash map", "Linked list", "Stack"],
                    "answer": "Hash map",
                    "explanation": "Hash maps use hashing for average constant-time lookups.",
                },
                {
                    "question": "What is the space complexity of merge sort?",
                    "options": ["O(1)", "O(log n)", "O(n)", "O(n^2)"],
                    "answer": "O(n)",
                    "explanation": "Merge sort typically requires an auxiliary array of size n.",
                },
                {
                    "question": "Which SQL clause is used to filter aggregated rows?",
                    "options": ["WHERE", "HAVING", "ORDER BY", "GROUP BY"],
                    "answer": "HAVING",
                    "explanation": "HAVING filters after GROUP BY aggregation is applied.",
                },
            ]
        )

    def _default_test_cases(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "tc_1",
                "input": "Typical valid input",
                "expectedOutput": "Expected result for valid input",
                "isHidden": False,
                "weight": 2,
            },
            {
                "id": "tc_2",
                "input": "Edge case input",
                "expectedOutput": "Expected edge-case result",
                "isHidden": True,
                "weight": 3,
            },
            {
                "id": "tc_3",
                "input": "Invalid or empty input",
                "expectedOutput": "Graceful fallback output",
                "isHidden": True,
                "weight": 2,
            },
        ]

    def _to_public_payload(self, full_payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            public_payload = json.loads(json.dumps(full_payload, ensure_ascii=True))
        except Exception:
            public_payload = dict(full_payload)

        challenge_type = str(public_payload.get("challengeType") or "coding").lower()
        if challenge_type == "mcq":
            raw_questions = public_payload.get("questions")
            if isinstance(raw_questions, list):
                sanitized_questions = []
                for question in raw_questions:
                    if not isinstance(question, dict):
                        continue
                    cleaned = dict(question)
                    cleaned.pop("correctOptionId", None)
                    sanitized_questions.append(cleaned)
                public_payload["questions"] = sanitized_questions
            return public_payload

        raw_test_cases = public_payload.get("testCases")
        if isinstance(raw_test_cases, list):
            sanitized_cases = []
            for case in raw_test_cases:
                if not isinstance(case, dict):
                    continue
                cleaned_case = dict(case)
                if bool(cleaned_case.get("isHidden", False)):
                    cleaned_case.pop("expectedOutput", None)
                sanitized_cases.append(cleaned_case)
            public_payload["testCases"] = sanitized_cases
        return public_payload

    async def _store_assessment_payload(self, token: str, email: str, payload: Dict[str, Any]) -> None:
        key = self._assessment_payload_key(token=token, email=email)
        try:
            redis_client = RedisManager.get_client()
            await redis_client.set(key, json.dumps(payload, ensure_ascii=True), ex=7200)
        except Exception as exc:
            logger.debug("Unable to persist assessment payload in Redis: %s", exc)

    async def _load_assessment_payload(self, token: str, email: str) -> Optional[Dict[str, Any]]:
        key = self._assessment_payload_key(token=token, email=email)
        try:
            redis_client = RedisManager.get_client()
            raw = await redis_client.get(key)
            if not raw:
                return None
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @staticmethod
    def _assessment_payload_key(token: str, email: str) -> str:
        return f"assessment_question:{str(token).strip()}:{str(email).strip().lower()}"

    @staticmethod
    def _detect_challenge_type(config: AgentRoundConfig) -> str:
        interview_mode = (getattr(config, "interview_mode", "") or "").strip().lower()
        if interview_mode in {"mcq", "quiz", "mcq_quiz", "aptitude", "apti", "apti_screening"}:
            return "mcq"
        if interview_mode in {"coding", "code", "coding_challenge"}:
            return "coding"

        coding_enabled = bool(getattr(config, "coding_enabled", False))
        mcq_enabled = bool(getattr(config, "mcq_enabled", False))
        if mcq_enabled and not coding_enabled:
            return "mcq"
        return "coding"

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @staticmethod
    def _coerce_score(raw_score: Any, default: int) -> int:
        try:
            value = int(raw_score)
        except Exception:
            value = default
        return max(0, min(100, value))

    @staticmethod
    def _can_call_groq() -> bool:
        if AsyncGroq is None:
            return False
        api_key = (getattr(settings, "effective_groq_api_key", "") or "").strip()
        return api_key.startswith("gsk_")
