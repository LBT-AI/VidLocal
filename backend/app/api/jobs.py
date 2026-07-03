from fastapi import APIRouter
from celery.result import AsyncResult
from app.workers.celery_app import celery_app
from app.schemas.common import APIResponse, JobStatusResponse

router = APIRouter()


@router.get("/{job_id}", response_model=APIResponse[JobStatusResponse])
async def get_job_status(job_id: str):
    task = AsyncResult(job_id, app=celery_app)
    progress = None
    if task.info and isinstance(task.info, dict):
        progress = task.info.get("progress")
    return APIResponse(data=JobStatusResponse(
        job_id=job_id,
        status=task.status,
        progress=progress,
        error=str(task.result) if task.failed() else None
    ))
