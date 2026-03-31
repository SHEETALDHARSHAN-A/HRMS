import logging
import uuid
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.orm import selectinload

from app.db.models.job_post_model import JobDetails
from app.db.models.agent_config_model import AgentRoundConfig
from app.schemas.config_request import AgentRoundConfigUpdate
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def _clean_str_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    cleaned: List[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def _coerce_count(raw: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except Exception:
        value = default
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value

class AgentConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_job_agent_config(
        self,
        job_id: str,
        user_id: str,
        rounds_data: List[AgentRoundConfigUpdate]
    ) -> List[Dict[str, Any]]:
        """
        Upserts agent configurations for a given job.
        Verifies user ownership before proceeding.
        """
        try:
            job_uuid = uuid.UUID(job_id)
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Job or User ID format")

        # 1. Verify Ownership
        job = await self.db.get(JobDetails, job_uuid)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        if job.user_id != user_uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to configure this job")

        # 2. Process all rounds in the request
        updated_configs_orm = []
        
        # Get all existing configs for this job for quick lookup
        existing_configs_stmt = select(AgentRoundConfig).where(AgentRoundConfig.job_id == job_uuid)
        existing_configs_result = await self.db.execute(existing_configs_stmt)
        # Map by RoundList.id
        existing_configs_map = {str(c.round_list_id): c for c in existing_configs_result.scalars().all()}

        for round_data in rounds_data:
            if round_data.jobId != job_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payload: Round config {round_data.roundName} references wrong job ID.")
            
            try:
                round_list_uuid = uuid.UUID(round_data.roundListId)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid roundListId: {round_data.roundListId}")

            config_payload = {
                "round_focus": round_data.roundFocus,
                "persona": round_data.persona,
                "key_skills": round_data.keySkills,
                "custom_questions": round_data.customQuestions,
                "forbidden_topics": round_data.forbiddenTopics,
                "coding_enabled": bool(getattr(round_data, "codingEnabled", getattr(round_data, "coding_enabled", False))),
                "coding_question_mode": getattr(round_data, "codingQuestionMode", getattr(round_data, "coding_question_mode", "ai")) or "ai",
                "coding_difficulty": getattr(round_data, "codingDifficulty", getattr(round_data, "coding_difficulty", "medium")) or "medium",
                "coding_languages": getattr(round_data, "codingLanguages", getattr(round_data, "coding_languages", ["python"])) or ["python"],
                "provided_coding_question": getattr(round_data, "providedCodingQuestion", getattr(round_data, "provided_coding_question", None)),
                "coding_test_case_mode": getattr(round_data, "codingTestCaseMode", getattr(round_data, "coding_test_case_mode", "ai")) or "ai",
                "coding_test_cases": getattr(round_data, "codingTestCases", getattr(round_data, "coding_test_cases", [])) or [],
                "coding_starter_code": getattr(round_data, "codingStarterCode", getattr(round_data, "coding_starter_code", {})) or {},
                "mcq_enabled": bool(getattr(round_data, "mcqEnabled", getattr(round_data, "mcq_enabled", False))),
                "mcq_question_mode": getattr(round_data, "mcqQuestionMode", getattr(round_data, "mcq_question_mode", "ai")) or "ai",
                "mcq_difficulty": getattr(round_data, "mcqDifficulty", getattr(round_data, "mcq_difficulty", "medium")) or "medium",
                "mcq_questions": getattr(round_data, "mcqQuestions", getattr(round_data, "mcq_questions", [])) or [],
                "mcq_passing_score": getattr(round_data, "mcqPassingScore", getattr(round_data, "mcq_passing_score", 60)) or 60,
                "round_name": round_data.roundName,
                "job_id": job_uuid,
                "round_list_id": round_list_uuid
            }

            assessment_settings = {
                "coding_question_count": _coerce_count(
                    getattr(round_data, "codingQuestionCount", getattr(round_data, "coding_question_count", 1)),
                    default=1,
                    minimum=1,
                    maximum=20,
                ),
                "coding_question_type": str(
                    getattr(round_data, "codingQuestionType", getattr(round_data, "coding_question_type", "")) or ""
                ).strip().lower() or None,
                "coding_categories": _clean_str_list(
                    getattr(round_data, "codingCategories", getattr(round_data, "coding_categories", []))
                ),
                "coding_custom_questions": _clean_str_list(
                    getattr(round_data, "codingCustomQuestions", getattr(round_data, "coding_custom_questions", []))
                ),
                "mcq_question_count": _coerce_count(
                    getattr(round_data, "mcqQuestionCount", getattr(round_data, "mcq_question_count", 5)),
                    default=5,
                    minimum=1,
                    maximum=100,
                ),
                "mcq_question_type": str(
                    getattr(round_data, "mcqQuestionType", getattr(round_data, "mcq_question_type", "")) or ""
                ).strip().lower() or None,
                "mcq_categories": _clean_str_list(
                    getattr(round_data, "mcqCategories", getattr(round_data, "mcq_categories", []))
                ),
                "mcq_custom_questions": (
                    getattr(round_data, "mcqCustomQuestions", getattr(round_data, "mcq_custom_questions", [])) or []
                ),
            }

            # Support apti aliases from frontend payloads.
            apti_count = getattr(round_data, "aptiQuestionCount", getattr(round_data, "apti_question_count", None))
            if apti_count is not None:
                assessment_settings["mcq_question_count"] = _coerce_count(apti_count, default=5, minimum=1, maximum=100)

            apti_type = getattr(round_data, "aptiQuestionType", getattr(round_data, "apti_question_type", None))
            if apti_type is not None:
                assessment_settings["mcq_question_type"] = str(apti_type or "").strip().lower() or None

            apti_categories = getattr(round_data, "aptiCategories", getattr(round_data, "apti_categories", None))
            if apti_categories:
                assessment_settings["mcq_categories"] = _clean_str_list(apti_categories)

            apti_custom = getattr(round_data, "aptiCustomQuestions", getattr(round_data, "apti_custom_questions", None))
            if apti_custom:
                assessment_settings["mcq_custom_questions"] = apti_custom or []

            # Always accept an explicit score distribution or individual metrics/thresholds
            # and store them under `score_distribution` on the config payload.
            if hasattr(round_data, 'scoreDistribution') and round_data.scoreDistribution is not None:
                config_payload['score_distribution'] = round_data.scoreDistribution
            else:
                # Accept legacy camelCase/snake_case if present
                if hasattr(round_data, 'score_distribution') and round_data.score_distribution is not None:
                    config_payload['score_distribution'] = round_data.score_distribution

                # Accept role/potential/location metrics if provided
                if getattr(round_data, 'roleFit', None) is not None:
                    config_payload.setdefault('score_distribution', {})['role_fit'] = round_data.roleFit
                if getattr(round_data, 'role_fit', None) is not None:
                    config_payload.setdefault('score_distribution', {})['role_fit'] = round_data.role_fit
                if getattr(round_data, 'potentialFit', None) is not None:
                    config_payload.setdefault('score_distribution', {})['potential'] = round_data.potentialFit
                if getattr(round_data, 'potential_fit', None) is not None:
                    config_payload.setdefault('score_distribution', {})['potential'] = round_data.potential_fit
                if getattr(round_data, 'locationFit', None) is not None:
                    config_payload.setdefault('score_distribution', {})['location'] = round_data.locationFit
                if getattr(round_data, 'location_fit', None) is not None:
                    config_payload.setdefault('score_distribution', {})['location'] = round_data.location_fit

                # Accept per-round thresholds if provided
                if getattr(round_data, 'shortlistingThreshold', None) is not None:
                    config_payload.setdefault('score_distribution', {})['shortlisting'] = round_data.shortlistingThreshold
                if getattr(round_data, 'shortlisting_threshold', None) is not None:
                    config_payload.setdefault('score_distribution', {})['shortlisting'] = round_data.shortlisting_threshold
                if getattr(round_data, 'rejectingThreshold', None) is not None:
                    config_payload.setdefault('score_distribution', {})['rejecting'] = round_data.rejectingThreshold
                if getattr(round_data, 'rejecting_threshold', None) is not None:
                    config_payload.setdefault('score_distribution', {})['rejecting'] = round_data.rejecting_threshold

            if not isinstance(config_payload.get("score_distribution"), dict):
                config_payload["score_distribution"] = {}
            config_payload["score_distribution"]["assessment_settings"] = assessment_settings
            
            # Check if this is an update or a new config
            existing_config = existing_configs_map.get(str(round_list_uuid))
            
            if existing_config:
                # UPDATE existing config
                logger.info(f"Updating config for round {round_list_uuid}")
                stmt = (
                    update(AgentRoundConfig)
                    .where(AgentRoundConfig.id == existing_config.id)
                    .values(**config_payload)
                    .returning(AgentRoundConfig)
                )
                result = await self.db.execute(stmt)
                updated_configs_orm.append(result.scalar_one())
            else:
                # INSERT new config
                logger.info(f"Inserting new config for round {round_list_uuid}")
                stmt = (
                    insert(AgentRoundConfig)
                    .values(id=uuid.uuid4(), **config_payload)
                    .returning(AgentRoundConfig)
                )
                result = await self.db.execute(stmt)
                updated_configs_orm.append(result.scalar_one())
        
        await self.db.commit()

        # 3. Serialize and return the updated data
        return [
            {
                "id": str(config.id),
                "jobId": str(config.job_id),
                "roundListId": str(config.round_list_id),
                "roundName": config.round_name,
                "roundFocus": config.round_focus,
                "persona": config.persona,
                "keySkills": config.key_skills,
                "customQuestions": config.custom_questions,
                "forbiddenTopics": config.forbidden_topics,
                "codingEnabled": bool(getattr(config, "coding_enabled", False)),
                "codingQuestionMode": getattr(config, "coding_question_mode", "ai"),
                "codingDifficulty": getattr(config, "coding_difficulty", "medium"),
                "codingLanguages": getattr(config, "coding_languages", None) or ["python"],
                "providedCodingQuestion": getattr(config, "provided_coding_question", None),
                "codingTestCaseMode": getattr(config, "coding_test_case_mode", "ai"),
                "codingTestCases": getattr(config, "coding_test_cases", None) or [],
                "codingStarterCode": getattr(config, "coding_starter_code", None) or {},
                "mcqEnabled": bool(getattr(config, "mcq_enabled", False)),
                "mcqQuestionMode": getattr(config, "mcq_question_mode", "ai"),
                "mcqDifficulty": getattr(config, "mcq_difficulty", "medium"),
                "mcqQuestions": getattr(config, "mcq_questions", None) or [],
                "mcqPassingScore": getattr(config, "mcq_passing_score", 60),
                "codingQuestionCount": (
                    (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("coding_question_count"))
                    or 1
                ),
                "codingQuestionType": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("coding_question_type")),
                "codingCategories": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("coding_categories")) or [],
                "codingCustomQuestions": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("coding_custom_questions")) or [],
                "mcqQuestionCount": (
                    (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_question_count"))
                    or 5
                ),
                "mcqQuestionType": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_question_type")),
                "mcqCategories": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_categories")) or [],
                "mcqCustomQuestions": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_custom_questions")) or [],
                "aptiQuestionCount": (
                    (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_question_count"))
                    or 5
                ),
                "aptiQuestionType": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_question_type")),
                "aptiCategories": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_categories")) or [],
                "aptiCustomQuestions": (((getattr(config, "score_distribution", None) or {}).get("assessment_settings", {}) or {}).get("mcq_custom_questions")) or [],
                "scoreDistribution": config.score_distribution,
                "shortlistingThreshold": (config.score_distribution or {}).get('shortlisting') if config.score_distribution is not None else None,
                "rejectingThreshold": (config.score_distribution or {}).get('rejecting') if config.score_distribution is not None else None,
            } for config in updated_configs_orm
        ]