import logging
from typing import List
import uuid
from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.connection_manager import get_db
from app.utils.standard_response_utils import ResponseBuilder
from app.schemas.standard_response import StandardResponse
from app.services.config_service.agent_config_service import AgentConfigService
from app.schemas.config_request import AgentConfigUpdateRequest # Import the new schema

logger = logging.getLogger(__name__)
agent_config_router = APIRouter(prefix="/agent-config", tags=["Agent Configuration"])

def _get_current_user_id(request: Request) -> str:
    user = getattr(getattr(request, "state", None), "user", None)
    if not user or not user.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    # Use 'sub' as the user_id, which corresponds to user.user_id in the DB
    return user.get("sub") 

@agent_config_router.post(
    "/job/{job_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Agent Configuration for a Job"
)
async def update_agent_config_route(
    job_id: str,
    request: Request,
    config_update: AgentConfigUpdateRequest, # Use the Pydantic model
    db: AsyncSession = Depends(get_db)
):
    """
    Updates (upserts) the agent configuration for all rounds of a specific job.
    """
    try:
        user_id = _get_current_user_id(request)
        
        # Validate job_id format
        try:
            uuid.UUID(job_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format")
            
        service = AgentConfigService(db)
        
        # Pass the list of rounds from the request body
        updated_configs = await service.update_job_agent_config(
            job_id=job_id,
            user_id=user_id,
            rounds_data=config_update.agentRounds
        )
        
        return ResponseBuilder.success(
            message="Agent configuration updated successfully.",
            data={"agentRounds": updated_configs}
        )
    except HTTPException as e:
        # Forward HTTPExceptions (like 403, 404) from the service
        return ResponseBuilder.error(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error updating agent config for job {job_id}: {e}", exc_info=True)
        return ResponseBuilder.server_error("An unexpected error occurred while saving configuration.")