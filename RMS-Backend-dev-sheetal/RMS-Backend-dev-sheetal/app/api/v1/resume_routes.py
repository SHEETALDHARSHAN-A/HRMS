# app/api/v1/resume_routes.py

from typing import List
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, UploadFile, File, status, Depends

from app.db.connection_manager import get_db
from app.schemas.standard_response import StandardResponse
from app.controllers.resume_controller import upload_resumes_controller

router = APIRouter(tags=["Resumes"])

@router.post(
    "/upload-resumes/{job_id}",
    summary="Upload resumes and enqueue job for processing",
    response_model=StandardResponse,
    description="""
    Upload multiple resume files (PDF/DOCX) for a given Job ID (`job_id`),
    store them locally under C:\\workspace\\resumes\\{job_id},
    and enqueue them for AI-based background processing in Redis.
    """,
)
async def upload_resumes_route(
    job_id: str,
    files: List[UploadFile] = File(..., description="List of resume files to upload"),
    db: AsyncSession = Depends(get_db)
):
    """Endpoint to upload multiple resumes and queue them for processing."""
    try:
        result = await upload_resumes_controller(job_id=job_id, files=files, db=db)
        
        response_status = result.get("status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return JSONResponse(
            status_code=response_status,
            content=result,
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=StandardResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to upload or queue resumes.",
                errors=[str(e)],
            ).model_dump(),
        )