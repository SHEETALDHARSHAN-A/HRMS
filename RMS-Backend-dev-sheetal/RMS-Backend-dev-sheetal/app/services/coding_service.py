import asyncio
import ast
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
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

    async def run_solution(self, request: CodingSubmitRequest) -> Dict[str, Any]:
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

        if challenge_type == "mcq":
            submitted_answers = [
                {"questionId": item.questionId, "selectedOptionId": item.selectedOptionId}
                for item in (request.mcqAnswers or [])
            ]
            evaluation = self._evaluate_mcq_submission(
                question_payload=question_payload,
                mcq_answers=submitted_answers,
            )
            return {
                "challengeType": "mcq",
                "score": evaluation.get("score"),
                "feedback": evaluation.get("feedback"),
                "breakdown": evaluation.get("breakdown"),
                "testCaseResults": evaluation.get("testCaseResults"),
                "evaluationSource": evaluation.get("evaluationSource"),
                "passed": evaluation.get("passed"),
                "maxScore": evaluation.get("maxScore"),
                "securityValidation": security_validation,
                "saved": False,
            }

        submission_code = (request.code or "").strip()
        if not submission_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code is required to run this coding submission",
            )

        allowed_languages = self._normalize_languages(getattr(context["config"], "coding_languages", None))
        requested_language = self._canonical_language(request.language or allowed_languages[0])
        if requested_language not in allowed_languages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported language '{requested_language}'. Allowed: {', '.join(allowed_languages)}. "
                    "Update round codingLanguages configuration to enable additional languages."
                ),
            )

        selected_question_payload = self._select_coding_question_payload(
            question_payload=question_payload,
            requested_question_id=getattr(request, "questionId", None),
        )
        normalized_test_cases = self._normalize_test_cases(selected_question_payload.get("testCases"))
        evaluation = await self._evaluate_test_cases(
            question_payload=selected_question_payload,
            code=submission_code,
            language=requested_language,
            test_cases=normalized_test_cases,
            allow_ai_fallback=False,
        )

        return {
            "challengeType": "coding",
            "language": requested_language,
            "score": evaluation.get("score"),
            "summary": evaluation.get("summary"),
            "testCaseResults": evaluation.get("results"),
            "evaluationSource": evaluation.get("source"),
            "strengths": evaluation.get("strengths") or [],
            "improvements": evaluation.get("improvements") or [],
            "question": selected_question_payload,
            "securityValidation": security_validation,
            "saved": False,
        }

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
        selected_question_payload = question_payload

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
                    detail=(
                        f"Unsupported language '{requested_language}'. Allowed: {', '.join(allowed_languages)}. "
                        "Update round codingLanguages configuration to enable additional languages."
                    ),
                )

            submission_language = requested_language
            selected_question_payload = self._select_coding_question_payload(
                question_payload=question_payload,
                requested_question_id=getattr(request, "questionId", None),
            )
            evaluation = await self._evaluate_coding_submission(
                question_payload=selected_question_payload,
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
            question_payload=selected_question_payload,
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

        response_payload = self._serialize_submission(submission)
        response_payload["securityValidation"] = security_validation
        return response_payload

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

        return self._serialize_submission(submission)

    async def get_latest_submission(self, token: str, email: str) -> Dict[str, Any]:
        context = await self._resolve_candidate_context(token=token, email=email)

        stmt = (
            select(CodingSubmission)
            .where(CodingSubmission.profile_id == context["profile_id"])
            .where(CodingSubmission.interview_token == token)
            .order_by(CodingSubmission.created_at.desc(), CodingSubmission.updated_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        submission = result.scalar_one_or_none()

        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No submission found yet")

        return self._serialize_submission(submission)

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
        enforce_security = bool(policy.get("enforceSecurity", False))
        secure_required = enforce_security and bool(policy.get("secureBrowserRequired", False))
        proctor_required = enforce_security and bool(policy.get("proctoringRequired", False))

        if not enforce_security or (not secure_required and not proctor_required):
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
            "enforceSecurity": enforce_security,
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
        if question_mode not in {"ai", "provided"}:
            question_mode = "ai"
        difficulty = (getattr(config, "coding_difficulty", "medium") or "medium").lower()
        languages = self._normalize_languages(getattr(config, "coding_languages", None))
        provided_question = (getattr(config, "provided_coding_question", None) or "").strip()

        settings = self._get_assessment_settings(config)
        question_count = self._coerce_count(
            settings.get("coding_question_count"),
            default=1,
            minimum=1,
            maximum=20,
        )
        question_type = str(settings.get("coding_question_type") or "").strip().lower() or None
        categories = self._normalize_string_list(settings.get("coding_categories"))
        custom_prompts = self._normalize_string_list(settings.get("coding_custom_questions"))
        if not custom_prompts:
            custom_prompts = self._normalize_string_list(getattr(config, "custom_questions", None))

        base_questions: List[Dict[str, Any]] = []
        if question_mode == "provided" and provided_question:
            base_questions.append(
                self._build_custom_coding_question(
                    prompt=provided_question,
                    title=f"{getattr(config, 'round_name', 'Coding Round')} Challenge",
                    source="provided",
                    question_type=question_type,
                    categories=categories,
                )
            )

        for custom_prompt in custom_prompts:
            if len(base_questions) >= question_count:
                break
            base_questions.append(
                self._build_custom_coding_question(
                    prompt=custom_prompt,
                    title=f"Custom Coding Challenge {len(base_questions) + 1}",
                    source="custom",
                    question_type=question_type,
                    categories=categories,
                )
            )

        while len(base_questions) < question_count:
            guidance = None
            if len(custom_prompts) > len(base_questions):
                guidance = custom_prompts[len(base_questions)]
            generated_question = await self._generate_ai_question(
                config=config,
                difficulty=difficulty,
                languages=languages,
                question_type=question_type,
                categories=categories,
                custom_guidance=guidance,
                question_index=len(base_questions) + 1,
                question_count=question_count,
            )
            base_questions.append(generated_question)

        test_case_mode = (getattr(config, "coding_test_case_mode", "ai") or "ai").lower()
        if test_case_mode not in {"ai", "provided"}:
            test_case_mode = "ai"
        configured_test_cases = self._normalize_test_cases(getattr(config, "coding_test_cases", None))

        starter_code = self._build_starter_code(
            languages=languages,
            configured_starter=getattr(config, "coding_starter_code", None),
        )

        question_pool: List[Dict[str, Any]] = []
        for idx, raw_question in enumerate(base_questions):
            normalized_question = {
                "id": str(raw_question.get("id") or f"coding_q_{idx + 1}"),
                "source": str(raw_question.get("source") or "ai"),
                "title": str(raw_question.get("title") or f"Coding Challenge {idx + 1}"),
                "problem": str(raw_question.get("problem") or "Solve the coding task."),
                "inputFormat": str(raw_question.get("inputFormat", raw_question.get("input_format", "")) or "").strip() or None,
                "outputFormat": str(raw_question.get("outputFormat", raw_question.get("output_format", "")) or "").strip() or None,
                "examples": self._normalize_examples(raw_question.get("examples")),
                "constraints": [
                    str(item).strip()
                    for item in (raw_question.get("constraints") or [])
                    if str(item).strip()
                ],
                "hints": [
                    str(item).strip()
                    for item in (raw_question.get("hints") or [])
                    if str(item).strip()
                ],
            }

            if not normalized_question["constraints"]:
                normalized_question["constraints"] = [
                    "Write clean, readable code.",
                    "Handle invalid and edge inputs safely.",
                ]

            if test_case_mode == "provided" and configured_test_cases:
                test_cases = configured_test_cases
            else:
                generated = await self._generate_ai_test_cases(
                    question_payload=normalized_question,
                    language=languages[0],
                    difficulty=difficulty,
                )
                test_cases = generated or configured_test_cases or self._default_test_cases()

            normalized_question["difficulty"] = difficulty
            normalized_question["languages"] = languages
            normalized_question["questionMode"] = question_mode
            normalized_question["testCaseMode"] = test_case_mode
            normalized_question["testCases"] = test_cases
            normalized_question["starterCode"] = starter_code
            normalized_question["questionType"] = question_type
            normalized_question["categories"] = categories
            normalized_question = self._ensure_coding_question_details(
                question_payload=normalized_question,
                test_cases=test_cases,
            )
            question_pool.append(normalized_question)

        if not question_pool:
            fallback_test_cases = configured_test_cases or self._default_test_cases()
            fallback_question = {
                "id": "coding_q_1",
                "source": "fallback",
                "title": "Coding Challenge",
                "problem": "Solve the coding task.",
                "inputFormat": "Input is provided to solve(input_data).",
                "outputFormat": "Return the expected answer for the given input.",
                "examples": [],
                "constraints": ["Handle edge cases and invalid input."],
                "hints": [],
                "difficulty": difficulty,
                "languages": languages,
                "questionMode": question_mode,
                "testCaseMode": test_case_mode,
                "testCases": fallback_test_cases,
                "starterCode": starter_code,
                "questionType": question_type,
                "categories": categories,
            }
            question_pool.append(
                self._ensure_coding_question_details(
                    question_payload=fallback_question,
                    test_cases=fallback_test_cases,
                )
            )

        active_question = dict(question_pool[0])
        active_question["questionPool"] = question_pool
        active_question["questionCountConfigured"] = question_count
        active_question["questionType"] = question_type
        active_question["questionCategories"] = categories
        active_question["customQuestionPrompts"] = custom_prompts
        return active_question

    async def _build_mcq_question(self, config: AgentRoundConfig) -> Dict[str, Any]:
        question_mode = (getattr(config, "mcq_question_mode", "ai") or "ai").lower()
        if question_mode not in {"ai", "provided"}:
            question_mode = "ai"
        difficulty = (getattr(config, "mcq_difficulty", "medium") or "medium").lower()
        configured_questions = self._normalize_mcq_questions(getattr(config, "mcq_questions", None))

        settings = self._get_assessment_settings(config)
        question_count = self._coerce_count(
            settings.get("mcq_question_count"),
            default=5,
            minimum=1,
            maximum=100,
        )
        question_type = str(settings.get("mcq_question_type") or "").strip().lower() or None
        categories = self._normalize_string_list(settings.get("mcq_categories"))

        raw_custom_mcq = settings.get("mcq_custom_questions")
        custom_question_bank = self._normalize_mcq_questions(raw_custom_mcq)
        custom_prompts: List[str] = []
        if isinstance(raw_custom_mcq, list):
            for item in raw_custom_mcq:
                if isinstance(item, str) and item.strip():
                    custom_prompts.append(item.strip())

        if question_mode == "provided":
            questions = custom_question_bank or configured_questions
            source = "provided"
            if len(questions) < question_count and custom_prompts:
                generated_questions = await self._generate_ai_mcq_questions(
                    config=config,
                    difficulty=difficulty,
                    question_count=question_count - len(questions),
                    question_type=question_type,
                    categories=categories,
                    custom_prompts=custom_prompts,
                )
                if generated_questions:
                    questions = questions + generated_questions
        else:
            generated_questions = await self._generate_ai_mcq_questions(
                config=config,
                difficulty=difficulty,
                question_count=question_count,
                question_type=question_type,
                categories=categories,
                custom_prompts=custom_prompts,
            )
            questions = generated_questions or custom_question_bank or configured_questions
            source = "ai" if generated_questions else "provided"

        if not questions:
            questions = self._fallback_mcq_questions()

        questions = self._top_up_mcq_questions(questions=questions, target_count=question_count)
        for question in questions:
            if not isinstance(question, dict):
                continue
            question.setdefault("questionType", question_type)
            if not question.get("categories"):
                question["categories"] = list(categories)

        passing_score = self._coerce_score(getattr(config, "mcq_passing_score", 60), default=60)

        return {
            "source": source,
            "title": f"{getattr(config, 'round_name', 'MCQ Round')} MCQ Challenge",
            "instructions": "Choose the best answer for each question.",
            "difficulty": difficulty,
            "questionMode": question_mode,
            "questionCountConfigured": question_count,
            "questionType": question_type,
            "questionCategories": categories,
            "customQuestionPrompts": custom_prompts,
            "questions": questions[:question_count],
            "passingScore": passing_score,
        }

    async def _generate_ai_question(
        self,
        config: AgentRoundConfig,
        difficulty: str,
        languages: List[str],
        question_type: Optional[str] = None,
        categories: Optional[List[str]] = None,
        custom_guidance: Optional[str] = None,
        question_index: int = 1,
        question_count: int = 1,
    ) -> Dict[str, Any]:
        skills = getattr(config, "key_skills", None) or []
        focus = getattr(config, "round_focus", None) or "data structures and problem solving"
        primary_skill = skills[0] if skills else "problem solving"
        category_text = ", ".join(categories or []) or "general"
        type_text = question_type or "problem solving"

        fallback_question = {
            "source": "ai",
            "title": f"{primary_skill.title()} Challenge",
            "problem": (
                f"Build a function in {languages[0]} to solve a {difficulty} level {primary_skill} task. "
                "Your function should handle edge cases and include a brief explanation of your approach."
            ),
            "inputFormat": "The input format is provided to your solve function as input_data.",
            "outputFormat": "Return the expected result for the provided input_data.",
            "examples": [
                {
                    "input": "input_data = [2, 7, 11, 15], target = 9",
                    "output": "[0, 1]",
                    "explanation": "Indices 0 and 1 add up to the target 9.",
                }
            ],
            "constraints": [
                "Time complexity should be explained.",
                "Handle invalid or empty input safely.",
            ],
            "hints": [
                "Start with a brute-force approach, then optimize.",
                "Think through edge cases before coding.",
            ],
            "questionType": type_text,
            "categories": categories or [],
        }

        if not self._can_call_groq():
            return fallback_question

        client = self._build_groq_client()
        prompt = f"""
Generate one coding interview question as strict JSON with keys:
- title (string)
- problem (string)
- inputFormat (string)
- outputFormat (string)
- examples (array of objects with input, output, explanation)
- constraints (array of strings)
- hints (array of strings)

Context:
- Round focus: {focus}
- Priority skills: {', '.join(skills) if skills else 'general coding'}
- Difficulty: {difficulty}
- Allowed languages: {', '.join(languages)}
- Question number: {question_index} of {question_count}
- Question type: {type_text}
- Categories: {category_text}
- Custom guidance: {custom_guidance or 'none'}

Requirements:
- Include at least one concrete sample input/output example.
- Keep all fields concise and implementation-ready.

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
            parsed.setdefault("inputFormat", fallback_question["inputFormat"])
            parsed.setdefault("outputFormat", fallback_question["outputFormat"])
            parsed_examples = self._normalize_examples(parsed.get("examples"))
            parsed["examples"] = parsed_examples or fallback_question["examples"]
            parsed.setdefault("constraints", fallback_question["constraints"])
            parsed.setdefault("hints", fallback_question["hints"])
            parsed["questionType"] = type_text
            parsed["categories"] = categories or []
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

        client = self._build_groq_client()
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

    async def _generate_ai_mcq_questions(
        self,
        config: AgentRoundConfig,
        difficulty: str,
        question_count: int = 5,
        question_type: Optional[str] = None,
        categories: Optional[List[str]] = None,
        custom_prompts: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self._can_call_groq():
            return []

        skills = getattr(config, "key_skills", None) or []
        focus = getattr(config, "round_focus", None) or "core fundamentals"
        question_count = self._coerce_count(question_count, default=5, minimum=1, maximum=100)
        type_text = question_type or "objective"
        category_text = ", ".join(categories or []) or "general aptitude"
        custom_text = ", ".join(custom_prompts or []) or "none"
        client = self._build_groq_client()

        prompt = f"""
Generate {question_count} MCQ interview questions as strict JSON object with key `questions`.

Each item in questions must include:
- question (string)
- options (array of exactly 4 option strings)
- answer (one option string that is correct)
- explanation (string)

Context:
- Round focus: {focus}
- Skills: {', '.join(skills) if skills else 'general aptitude and technical basics'}
- Difficulty: {difficulty}
- Question type: {type_text}
- Categories: {category_text}
- Custom prompts to include: {custom_text}
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
            return self._normalize_mcq_questions(parsed.get("questions"))[:question_count]
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
        allow_ai_fallback: bool = True,
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

        runtime_result = await self._evaluate_test_cases_runtime(
            code=code,
            language=language,
            test_cases=test_cases,
        )
        if runtime_result:
            return runtime_result

        if not allow_ai_fallback:
            language_name = self._canonical_language(language)
            return {
                "score": None,
                "results": [
                    {
                        "id": str(case.get("id") or ""),
                        "input": case.get("input"),
                        "expectedOutput": case.get("expectedOutput"),
                        "isHidden": bool(case.get("isHidden", False)),
                        "weight": int(case.get("weight", 1)),
                        "passed": False,
                        "actualOutput": None,
                        "notes": f"Runtime execution is currently unavailable for language '{language_name}'.",
                    }
                    for case in test_cases
                ],
                "summary": f"Runtime preview is unavailable for language '{language_name}'.",
                "source": "runtime-unavailable",
                "strengths": [],
                "improvements": ["Switch to Python/JavaScript runtime preview or submit for AI-assisted evaluation."],
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

    async def _evaluate_test_cases_runtime(
        self,
        *,
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        runtime_lang = self._canonical_language(language)
        runner = None
        runtime_source = ""
        runtime_label = ""

        if runtime_lang == "python":
            runner = self._run_python_case_sync
            runtime_source = "runtime-python"
            runtime_label = "Python runtime"
        elif runtime_lang == "javascript" and shutil.which("node"):
            runner = self._run_javascript_case_sync
            runtime_source = "runtime-javascript"
            runtime_label = "JavaScript runtime"

        if runner is None:
            return None

        raw_results: List[Dict[str, Any]] = []
        for case in test_cases:
            case_id = str(case.get("id") or "").strip() or f"tc_{len(raw_results) + 1}"
            expected_output = str(case.get("expectedOutput") or "").strip()
            runtime_input = self._parse_runtime_input(case.get("input"))

            runtime_eval = await asyncio.to_thread(
                runner,
                code,
                runtime_input,
            )

            if runtime_eval.get("ok"):
                return_text = self._normalize_runtime_output(runtime_eval.get("returnValue"))
                stdout_text = str(runtime_eval.get("stdout") or "").strip()
                actual_text = return_text
                if stdout_text:
                    actual_text = f"stdout: {stdout_text} | return: {return_text}"

                passed = self._runtime_outputs_match(
                    expected_output=expected_output,
                    return_output=return_text,
                    stdout_output=stdout_text,
                )
                notes = f"Executed in {runtime_label}."
            else:
                actual_text = str(runtime_eval.get("error") or "Runtime execution failed.")
                passed = False
                notes = "Runtime execution failed."

            raw_results.append(
                {
                    "id": case_id,
                    "passed": passed,
                    "actualOutput": actual_text,
                    "notes": notes,
                }
            )

        scored = self._score_test_case_results(test_cases=test_cases, raw_results=raw_results)
        scored["source"] = runtime_source

        if scored["score"] >= 80:
            scored["strengths"] = ["Outputs matched expected values for most test cases."]
            scored["improvements"] = []
        else:
            scored["strengths"] = []
            scored["improvements"] = ["Fix failing test cases by matching expected outputs exactly."]

        return scored

        def _run_javascript_case_sync(self, code: str, input_data: Any, timeout_seconds: int = 4) -> Dict[str, Any]:
                runner_script = textwrap.dedent(
                        """
                        const fs = require('fs');
                        const vm = require('vm');

                        const parseInput = (raw) => {
                            if (typeof raw !== 'string') return raw;
                            const text = raw.trim();
                            if (!text) return raw;
                            try { return JSON.parse(text); } catch (_) {}
                            return raw;
                        };

                        (async () => {
                            try {
                                const payload = JSON.parse(fs.readFileSync(0, 'utf8') || '{}');
                                const codePath = payload.codePath;
                                if (!codePath) throw new Error('Missing code path');

                                const userCode = fs.readFileSync(codePath, 'utf8');
                                const logs = [];
                                const sandbox = {
                                    console: {
                                        log: (...args) => logs.push(args.map((v) => String(v)).join(' ')),
                                    },
                                    module: { exports: {} },
                                    exports: {},
                                    require,
                                    JSON,
                                    Math,
                                    Date,
                                    setTimeout,
                                    clearTimeout,
                                };
                                vm.createContext(sandbox);
                                vm.runInContext(userCode, sandbox, { timeout: 2500 });

                                let solveFn = null;
                                if (typeof sandbox.solve === 'function') {
                                    solveFn = sandbox.solve;
                                } else if (
                                    sandbox.module &&
                                    sandbox.module.exports &&
                                    typeof sandbox.module.exports.solve === 'function'
                                ) {
                                    solveFn = sandbox.module.exports.solve;
                                }

                                if (!solveFn) {
                                    throw new Error("Function 'solve(input_data)' is not defined");
                                }

                                const parsedInput = parseInput(payload.input);
                                const value = solveFn(parsedInput);
                                const result = value && typeof value.then === 'function' ? await value : value;

                                process.stdout.write(
                                    JSON.stringify({
                                        ok: true,
                                        returnValue: result,
                                        stdout: logs.join('\\n'),
                                    })
                                );
                            } catch (err) {
                                process.stdout.write(
                                    JSON.stringify({
                                        ok: false,
                                        error: err && err.stack ? String(err.stack).split('\\n')[0] : String(err),
                                    })
                                );
                            }
                        })();
                        """
                ).strip()

                try:
                        with tempfile.TemporaryDirectory(prefix="rms_eval_js_") as tmp_dir:
                                code_path = f"{tmp_dir}/candidate_submission.js"
                                runner_path = f"{tmp_dir}/runner.js"

                                with open(code_path, "w", encoding="utf-8") as candidate_file:
                                        candidate_file.write(code)

                                with open(runner_path, "w", encoding="utf-8") as runner_file:
                                        runner_file.write(runner_script)

                                payload = json.dumps({"codePath": code_path, "input": input_data}, ensure_ascii=True)
                                completed = subprocess.run(
                                        ["node", runner_path],
                                        input=payload,
                                        text=True,
                                        capture_output=True,
                                        timeout=timeout_seconds,
                                )

                                stdout_text = (completed.stdout or "").strip()
                                stderr_text = (completed.stderr or "").strip()

                                if completed.returncode != 0:
                                        return {
                                                "ok": False,
                                                "error": stderr_text or stdout_text or f"Execution failed with exit code {completed.returncode}.",
                                        }

                                if not stdout_text:
                                        return {"ok": False, "error": "No runtime output received from evaluator."}

                                parsed = json.loads(stdout_text.splitlines()[-1])
                                if not isinstance(parsed, dict):
                                        return {"ok": False, "error": "Invalid runtime response format."}
                                if not parsed.get("ok"):
                                        return {"ok": False, "error": str(parsed.get("error") or "Runtime execution failed.")}

                                return {
                                        "ok": True,
                                        "returnValue": parsed.get("returnValue"),
                                        "stdout": str(parsed.get("stdout") or ""),
                                }
                except subprocess.TimeoutExpired:
                        return {"ok": False, "error": "Execution timed out."}
                except Exception as exc:
                        return {"ok": False, "error": f"Runtime execution unavailable: {exc}"}

    def _run_python_case_sync(self, code: str, input_data: Any, timeout_seconds: int = 4) -> Dict[str, Any]:
        runner_script = textwrap.dedent(
            """
            import ast
            import contextlib
            import importlib.util
            import io
            import json
            import sys
            import traceback

            def _parse_input(raw):
                if isinstance(raw, str):
                    txt = raw.strip()
                    if not txt:
                        return raw
                    for parser in (json.loads, ast.literal_eval):
                        try:
                            return parser(txt)
                        except Exception:
                            pass
                return raw

            try:
                payload = json.loads(sys.stdin.read() or "{}")
                code_path = payload.get("codePath")
                if not code_path:
                    raise ValueError("Missing code path")

                spec = importlib.util.spec_from_file_location("candidate_submission", code_path)
                module = importlib.util.module_from_spec(spec)
                if spec is None or spec.loader is None:
                    raise RuntimeError("Unable to load candidate module")

                output_buffer = io.StringIO()
                with contextlib.redirect_stdout(output_buffer):
                    spec.loader.exec_module(module)
                    solve = getattr(module, "solve", None)
                    if not callable(solve):
                        raise AttributeError("Function 'solve(input_data)' is not defined")
                    parsed_input = _parse_input(payload.get("input"))
                    result = solve(parsed_input)

                print(
                    json.dumps(
                        {
                            "ok": True,
                            "returnValue": result,
                            "stdout": output_buffer.getvalue(),
                        },
                        ensure_ascii=True,
                        default=str,
                    )
                )
            except Exception:
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "error": traceback.format_exc(limit=1),
                        },
                        ensure_ascii=True,
                    )
                )
            """
        ).strip()

        try:
            with tempfile.TemporaryDirectory(prefix="rms_eval_") as tmp_dir:
                code_path = f"{tmp_dir}/candidate_submission.py"
                runner_path = f"{tmp_dir}/runner.py"

                with open(code_path, "w", encoding="utf-8") as candidate_file:
                    candidate_file.write(code)

                with open(runner_path, "w", encoding="utf-8") as runner_file:
                    runner_file.write(runner_script)

                payload = json.dumps({"codePath": code_path, "input": input_data}, ensure_ascii=True)
                completed = subprocess.run(
                    [sys.executable, "-I", runner_path],
                    input=payload,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                )

                stdout_text = (completed.stdout or "").strip()
                stderr_text = (completed.stderr or "").strip()

                if completed.returncode != 0:
                    return {
                        "ok": False,
                        "error": stderr_text or stdout_text or f"Execution failed with exit code {completed.returncode}.",
                    }

                if not stdout_text:
                    return {"ok": False, "error": "No runtime output received from evaluator."}

                parsed = json.loads(stdout_text.splitlines()[-1])
                if not isinstance(parsed, dict):
                    return {"ok": False, "error": "Invalid runtime response format."}
                if not parsed.get("ok"):
                    return {"ok": False, "error": str(parsed.get("error") or "Runtime execution failed.")}

                return {
                    "ok": True,
                    "returnValue": parsed.get("returnValue"),
                    "stdout": str(parsed.get("stdout") or ""),
                }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Execution timed out."}
        except Exception as exc:
            return {"ok": False, "error": f"Runtime execution unavailable: {exc}"}

    @staticmethod
    def _parse_runtime_input(raw_input: Any) -> Any:
        if not isinstance(raw_input, str):
            return raw_input

        stripped = raw_input.strip()
        if not stripped:
            return raw_input

        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(stripped)
            except Exception:
                continue

        return raw_input

    @staticmethod
    def _normalize_runtime_output(value: Any) -> str:
        if value is None:
            return "None"
        if isinstance(value, str):
            return value.strip()
        try:
            return json.dumps(value, ensure_ascii=True, sort_keys=True)
        except Exception:
            return str(value).strip()

    @staticmethod
    def _runtime_outputs_match(*, expected_output: str, return_output: str, stdout_output: str) -> bool:
        expected = str(expected_output or "").strip()
        if not expected:
            return True

        expected_norm = re.sub(r"\s+", " ", expected).strip().lower()
        return_norm = re.sub(r"\s+", " ", str(return_output or "")).strip().lower()
        stdout_norm = re.sub(r"\s+", " ", str(stdout_output or "")).strip().lower()

        if expected_norm == return_norm or expected_norm == stdout_norm:
            return True
        if return_norm and expected_norm in return_norm:
            return True
        if stdout_norm and expected_norm in stdout_norm:
            return True
        return False

    async def _evaluate_test_cases_with_ai(
        self,
        question_payload: Dict[str, Any],
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self._can_call_groq():
            return None

        client = self._build_groq_client()
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
        client = self._build_groq_client()
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

    def _select_coding_question_payload(
        self,
        *,
        question_payload: Dict[str, Any],
        requested_question_id: Optional[str],
    ) -> Dict[str, Any]:
        if not isinstance(question_payload, dict):
            return {}

        pool = question_payload.get("questionPool")
        if not isinstance(pool, list) or not pool:
            return question_payload

        requested = str(requested_question_id or "").strip()
        selected = None
        if requested:
            for question in pool:
                if not isinstance(question, dict):
                    continue
                if str(question.get("id") or "").strip() == requested:
                    selected = question
                    break

        if selected is None:
            selected = pool[0] if isinstance(pool[0], dict) else None

        if selected is None:
            return question_payload

        selected_payload = dict(selected)
        selected_payload["challengeType"] = "coding"
        selected_payload["questionCountConfigured"] = question_payload.get("questionCountConfigured")
        selected_payload["questionType"] = question_payload.get("questionType")
        selected_payload["questionCategories"] = question_payload.get("questionCategories")
        selected_payload["selectedQuestionId"] = selected_payload.get("id")
        return selected_payload

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

    def _get_assessment_settings(self, config: AgentRoundConfig) -> Dict[str, Any]:
        score_distribution = getattr(config, "score_distribution", None)
        if not isinstance(score_distribution, dict):
            return {}

        settings = score_distribution.get("assessment_settings")
        if not isinstance(settings, dict):
            return {}

        return settings

    @staticmethod
    def _normalize_string_list(raw: Optional[Any]) -> List[str]:
        if not isinstance(raw, list):
            return []

        normalized: List[str] = []
        for item in raw:
            text = str(item or "").strip()
            if text:
                normalized.append(text)
        return normalized

    @staticmethod
    def _coerce_count(raw_count: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(raw_count)
        except Exception:
            value = default
        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value

    @staticmethod
    def _build_custom_coding_question(
        *,
        prompt: str,
        title: str,
        source: str,
        question_type: Optional[str],
        categories: Optional[List[str]],
    ) -> Dict[str, Any]:
        return {
            "source": source,
            "title": title,
            "problem": str(prompt or "").strip(),
            "inputFormat": "Use the function signature in starter code to parse input_data.",
            "outputFormat": "Return the computed answer in the expected format.",
            "examples": [
                {
                    "input": "Refer to the prompt for sample input.",
                    "output": "Return the expected output for that input.",
                    "explanation": "Show how the output is derived from the input.",
                }
            ],
            "constraints": [
                "Write clean, readable code.",
                "Handle invalid and edge inputs safely.",
            ],
            "hints": [
                "State your approach before coding.",
            ],
            "questionType": question_type,
            "categories": categories or [],
        }

    @staticmethod
    def _normalize_examples(raw_examples: Optional[Any]) -> List[Dict[str, str]]:
        if not isinstance(raw_examples, list):
            return []

        normalized: List[Dict[str, str]] = []
        for raw_item in raw_examples:
            if isinstance(raw_item, dict):
                sample_input = str(
                    raw_item.get("input", raw_item.get("sampleInput", raw_item.get("stdin", ""))) or ""
                ).strip()
                sample_output = str(
                    raw_item.get("output", raw_item.get("expectedOutput", raw_item.get("sampleOutput", ""))) or ""
                ).strip()
                explanation = str(raw_item.get("explanation", raw_item.get("note", "")) or "").strip()
            else:
                sample_input = ""
                sample_output = ""
                explanation = str(raw_item or "").strip()

            if not sample_input and not sample_output and not explanation:
                continue

            normalized.append(
                {
                    "input": sample_input,
                    "output": sample_output,
                    "explanation": explanation,
                }
            )

        return normalized[:5]

    @staticmethod
    def _examples_from_test_cases(test_cases: List[Dict[str, Any]], limit: int = 2) -> List[Dict[str, str]]:
        examples: List[Dict[str, str]] = []
        for case in test_cases:
            if bool(case.get("isHidden", False)):
                continue

            sample_input = str(case.get("input") or "").strip()
            sample_output = str(case.get("expectedOutput") or "").strip()
            if not sample_input and not sample_output:
                continue

            examples.append(
                {
                    "input": sample_input,
                    "output": sample_output,
                    "explanation": "Sample derived from visible test case.",
                }
            )
            if len(examples) >= limit:
                break

        return examples

    def _ensure_coding_question_details(
        self,
        *,
        question_payload: Dict[str, Any],
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        detailed = dict(question_payload)
        problem = str(detailed.get("problem") or "").strip() or "Solve the coding task."
        input_format = str(detailed.get("inputFormat") or "").strip() or "Input is provided to solve(input_data)."
        output_format = str(detailed.get("outputFormat") or "").strip() or "Return the expected result for input_data."

        examples = self._normalize_examples(detailed.get("examples"))
        if not examples:
            examples = self._examples_from_test_cases(test_cases=test_cases)
        if not examples:
            examples = [
                {
                    "input": "Sample input",
                    "output": "Sample output",
                    "explanation": "Explain how the sample output is derived from the sample input.",
                }
            ]

        detailed["problem"] = problem
        detailed["inputFormat"] = input_format
        detailed["outputFormat"] = output_format
        detailed["examples"] = examples

        existing_detailed_prompt = str(detailed.get("detailedPrompt") or "").strip()
        if not existing_detailed_prompt:
            lines = [
                problem,
                "",
                "Input Format:",
                input_format,
                "",
                "Output Format:",
                output_format,
                "",
                "Sample Input and Output:",
            ]
            for index, sample in enumerate(examples, start=1):
                lines.append(f"Example {index} Input: {sample.get('input') or 'N/A'}")
                lines.append(f"Example {index} Output: {sample.get('output') or 'N/A'}")
                explanation = str(sample.get("explanation") or "").strip()
                if explanation:
                    lines.append(f"Example {index} Explanation: {explanation}")
                lines.append("")
            detailed["detailedPrompt"] = "\n".join(lines).strip()

        return detailed

    def _top_up_mcq_questions(self, questions: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        target_count = self._coerce_count(target_count, default=5, minimum=1, maximum=100)
        normalized = self._normalize_mcq_questions(questions)
        if len(normalized) >= target_count:
            return normalized[:target_count]

        fallback_bank = self._fallback_mcq_questions()
        cursor = 0
        while len(normalized) < target_count and fallback_bank:
            seed = dict(fallback_bank[cursor % len(fallback_bank)])
            seed["id"] = f"q_{len(normalized) + 1}"
            normalized.append(seed)
            cursor += 1

        return normalized[:target_count]

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
                    "questionType": str(raw_question.get("questionType") or raw_question.get("question_type") or "").strip().lower() or None,
                    "categories": [
                        str(item).strip()
                        for item in (
                            raw_question.get("categories")
                            if isinstance(raw_question.get("categories"), list)
                            else []
                        )
                        if str(item).strip()
                    ],
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

        question_pool = public_payload.get("questionPool")
        if isinstance(question_pool, list):
            sanitized_pool: List[Dict[str, Any]] = []
            for question in question_pool:
                if not isinstance(question, dict):
                    continue
                cleaned_question = dict(question)
                pool_cases = cleaned_question.get("testCases")
                if isinstance(pool_cases, list):
                    sanitized_pool_cases = []
                    for case in pool_cases:
                        if not isinstance(case, dict):
                            continue
                        cleaned_case = dict(case)
                        if bool(cleaned_case.get("isHidden", False)):
                            cleaned_case.pop("expectedOutput", None)
                        sanitized_pool_cases.append(cleaned_case)
                    cleaned_question["testCases"] = sanitized_pool_cases
                sanitized_pool.append(cleaned_question)
            public_payload["questionPool"] = sanitized_pool
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
    def _serialize_submission(submission: CodingSubmission) -> Dict[str, Any]:
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

    @staticmethod
    def _build_groq_client() -> Any:
        api_key = settings.effective_groq_api_key
        base_url = (getattr(settings, "effective_groq_sdk_base_url", "") or "").strip()
        if not base_url:
            return AsyncGroq(api_key=api_key)
        try:
            return AsyncGroq(api_key=api_key, base_url=base_url)
        except TypeError:
            logger.warning("Groq SDK version does not accept base_url, using default client base URL")
            return AsyncGroq(api_key=api_key)
