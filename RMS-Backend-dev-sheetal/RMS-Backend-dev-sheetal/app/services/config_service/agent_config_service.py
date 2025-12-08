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
                "round_name": round_data.roundName,
                "job_id": job_uuid,
                "round_list_id": round_list_uuid
            }
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
                "scoreDistribution": config.score_distribution,
                "shortlistingThreshold": (config.score_distribution or {}).get('shortlisting') if config.score_distribution is not None else None,
                "rejectingThreshold": (config.score_distribution or {}).get('rejecting') if config.score_distribution is not None else None,
            } for config in updated_configs_orm
        ]