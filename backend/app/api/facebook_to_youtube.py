import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user
from app.models.video_job import VideoJob
from app.schemas.common import APIResponse, JobStatusResponse
from app.services.facebook_download_service import facebook_download_service
from app.workers.celery_app import celery_app

router = APIRouter()


class FacebookToYoutubeRequest(BaseModel):
    url: str
    privacy: str = "private"


class JobStatusOut(BaseModel):
    id: str
    type: str
    source_url: str
    status: str
    progress: int
    youtube_url: str | None = None
    error_message: str | None = None
    transcript: str | None = None
    transcript_language: str | None = None
    ai_title: str | None = None
    ai_description: str | None = None
    ai_tags: str | None = None
    ai_hashtags: str | None = None
    ai_summary: str | None = None
    ai_hook: str | None = None
    ai_category: str | None = None
    risk_flags: str | None = None
    metadata_status: str | None = None

    class Config:
        from_attributes = True


@router.post("/facebook-to-youtube", response_model=APIResponse[JobStatusResponse])
async def create_facebook_to_youtube_job(
    data: FacebookToYoutubeRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    if not facebook_download_service.validate_url(data.url):
        raise HTTPException(status_code=400, detail="Invalid Facebook URL")
    job = VideoJob(
        type="facebook_to_youtube",
        source_url=data.url,
        source_platform="facebook",
        target_platform="youtube",
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    task = celery_app.send_task(
        "workers.facebook_to_youtube_worker.process",
        args=[str(job.id)],
    )
    return APIResponse(
        data=JobStatusResponse(job_id=task.id, status="PENDING", progress=0.0),
        job_id=task.id,
    )


@router.get("/facebook-to-youtube/{job_id}", response_model=APIResponse[JobStatusOut])
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=JobStatusOut.model_validate(job))


@router.get("/facebook-to-youtube", response_model=APIResponse[list[JobStatusOut]])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(VideoJob).where(VideoJob.type == "facebook_to_youtube").order_by(VideoJob.created_at.desc()).limit(50)
    )
    jobs = result.scalars().all()
    return APIResponse(data=[JobStatusOut.model_validate(j) for j in jobs])
