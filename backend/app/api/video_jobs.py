import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models.video_job import VideoJob
from app.models.character_glossary_draft import CharacterGlossaryItem
from app.schemas.common import APIResponse
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateVideoJobRequest(BaseModel):
    url: str
    platform: str = "facebook"
    title: Optional[str] = None
    options: Optional[dict] = None


class VideoJobOut(BaseModel):
    id: str
    platform: str
    url: str
    title: str
    status: str
    progress: int
    created_time: str
    youtube_url: Optional[str] = None
    current_step: str = "download"
    steps: Optional[dict] = None
    transcript: Optional[str] = None
    glossary: Optional[List[dict]] = None
    metadata: Optional[dict] = None
    files: List[dict] = []
    logs: List[dict] = []
    options: Optional[dict] = None
    thumbnail: Optional[dict] = None

    class Config:
        from_attributes = True


def model_to_video_job_out(job: VideoJob) -> VideoJobOut:
    platform = job.source_platform or "facebook"
    step_map = {
        "pending": ("download", 0),
        "downloading": ("download", 15),
        "downloaded": ("transcribe", 30),
        "transcribing": ("transcribe", 40),
        "extracting_characters": ("character_extract", 55),
        "awaiting_glossary": ("glossary_review", 70),
        "metadata_generating": ("seo_metadata", 80),
        "waiting_approval": ("seo_metadata", 85),
        "processing": ("watermark", 90),
        "watermarking": ("watermark", 92),
        "uploading_youtube": ("upload", 95),
        "completed": ("done", 100),
        "failed": ("download", job.progress or 50),
    }
    current_step, progress = step_map.get(job.status, ("download", 0))

    steps = {
        "download": {"status": "completed" if job.status != "pending" else "pending", "progress": 100 if job.status not in ("pending",) else 0},
        "transcribe": {"status": "completed" if job.status in ("downloaded", "transcribing", "extracting_characters", "awaiting_glossary", "metadata_generating", "waiting_approval", "processing", "watermarking", "uploading_youtube", "completed") else "pending" if job.status in ("pending", "downloading") else "running", "progress": 100 if job.status in ("downloaded", "transcribing", "extracting_characters", "awaiting_glossary", "metadata_generating", "waiting_approval", "processing", "watermarking", "uploading_youtube", "completed") else 0 if job.status in ("pending", "downloading") else 50},
        "character_extract": {"status": "completed" if job.status in ("awaiting_glossary", "metadata_generating", "waiting_approval", "processing", "watermarking", "uploading_youtube", "completed") else "running" if job.status == "extracting_characters" else "pending", "progress": 100 if job.status in ("awaiting_glossary", "metadata_generating", "waiting_approval", "processing", "watermarking", "uploading_youtube", "completed") else 0 if job.status in ("pending", "downloading", "downloaded", "transcribing") else 50},
        "glossary_review": {"status": "completed" if job.glossary_status == "approved" else "running" if job.status == "awaiting_glossary" else "pending" if job.status not in ("awaiting_glossary",) else "running", "progress": 100 if job.glossary_status == "approved" else 0},
        "seo_metadata": {"status": "completed" if job.status in ("waiting_approval", "processing", "watermarking", "uploading_youtube", "completed") else "running" if job.status == "metadata_generating" else "pending", "progress": 100 if job.status in ("waiting_approval", "processing", "watermarking", "uploading_youtube", "completed") else 0 if job.status not in ("metadata_generating",) else 50},
        "watermark": {"status": "completed" if job.status in ("uploading_youtube", "completed") else "running" if job.status == "watermarking" else "pending" if job.status not in ("processing", "watermarking", "uploading_youtube", "completed") else "running", "progress": 100 if job.status == "uploading_youtube" or job.status == "completed" else 0 if job.status not in ("processing", "watermarking") else 50},
        "upload": {"status": "completed" if job.status == "completed" else "running" if job.status == "uploading_youtube" else "pending", "progress": 100 if job.status == "completed" else 0 if job.status not in ("uploading_youtube",) else 50},
    }

    glossary = None
    if job.glossary_status and job.glossary_draft_id:
        glossary = [{"id": str(job.glossary_draft_id), "source_name": "", "target_name": "", "status": job.glossary_status}]

    metadata = None
    if job.ai_title:
        metadata = {
            "title": job.ai_title,
            "description": job.ai_description or "",
            "tags": json.loads(job.ai_tags) if job.ai_tags else [],
            "hashtags": json.loads(job.ai_hashtags) if job.ai_hashtags else [],
            "summary": job.ai_summary or "",
            "hook": job.ai_hook or "",
            "category": job.ai_category or "",
            "risk_flags": json.loads(job.risk_flags) if job.risk_flags else [],
            "privacy": "private",
        }

    thumbnail = None
    if job.thumbnail_status:
        thumbnail = {
            "status": job.thumbnail_status,
            "prompts": json.loads(job.thumbnail_prompts) if job.thumbnail_prompts else [],
            "image_url": f"/data/thumbnails/{job.id}.jpg" if job.thumbnail_path else None,
        }

    return VideoJobOut(
        id=str(job.id),
        platform=platform,
        url=job.source_url,
        title=job.ai_title or job.source_url.split("/")[-1] if job.source_url else "Untitled",
        status=job.status,
        progress=progress,
        created_time=job.created_at.isoformat() if job.created_at else datetime.utcnow().isoformat(),
        youtube_url=job.youtube_url,
        current_step=current_step,
        steps=steps,
        transcript=job.transcript,
        glossary=glossary,
        metadata=metadata,
        thumbnail=thumbnail,
        options={
            "extract_characters": True,
            "generate_seo": True,
            "add_watermark": True,
            "upload_privacy": "private",
            "enable_dubbing": False,
        },
    )


@router.get("", response_model=APIResponse)
async def list_video_jobs(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    query = select(VideoJob).order_by(VideoJob.created_at.desc()).limit(50)
    if platform:
        query = query.where(VideoJob.source_platform == platform)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return APIResponse(data=[model_to_video_job_out(j) for j in jobs])


@router.post("", response_model=APIResponse)
async def create_video_job(
    data: CreateVideoJobRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    if data.platform == "facebook":
        from app.services.facebook_download_service import facebook_download_service
        if not facebook_download_service.validate_url(data.url):
            raise HTTPException(status_code=400, detail="Invalid Facebook URL")
        task_name = "workers.facebook_to_youtube_worker.process"
    elif data.platform == "tiktok":
        task_name = "workers.tiktok_to_youtube_worker.process"
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform. Use 'facebook' or 'tiktok'")

    title = data.title or data.url.split("/")[-1] or "Untitled"
    job = VideoJob(
        type=f"{data.platform}_to_youtube",
        source_url=data.url,
        source_platform=data.platform,
        target_platform="youtube",
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = celery_app.send_task(task_name, args=[str(job.id)])

    out = model_to_video_job_out(job)
    return APIResponse(data=out, job_id=task.id)


@router.get("/{job_id}", response_model=APIResponse)
async def get_video_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/approve-glossary", response_model=APIResponse)
async def approve_glossary(
    job_id: uuid.UUID,
    glossary: Optional[List[dict]] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.glossary_status = "approved"
    await db.commit()

    task_name = f"workers.{job.source_platform}_to_youtube_worker.process_after_glossary"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/skip-glossary", response_model=APIResponse)
async def skip_glossary(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.glossary_status = "skipped"
    await db.commit()

    task_name = f"workers.{job.source_platform}_to_youtube_worker.process_after_glossary"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/regenerate-metadata", response_model=APIResponse)
async def regenerate_metadata(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    task_name = f"workers.{job.source_platform}_to_youtube_worker.process_after_glossary"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job), message="Regenerating metadata")


@router.post("/{job_id}/approve-upload", response_model=APIResponse)
async def approve_upload(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "waiting_approval":
        raise HTTPException(status_code=400, detail=f"Job is in '{job.status}' state, not waiting_approval")
    job.status = "processing"
    await db.commit()

    task_name = f"workers.{job.source_platform}_to_youtube_worker.upload_approved"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/cancel", response_model=APIResponse)
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "failed"
    job.error_message = "Cancelled by user"
    await db.commit()
    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/retry", response_model=APIResponse)
async def retry_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "pending"
    job.error_message = None
    job.progress = 0
    await db.commit()

    task_name = f"workers.{job.source_platform}_to_youtube_worker.process"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/thumbnail-prompts", response_model=APIResponse)
async def generate_thumbnail_prompts(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=model_to_video_job_out(job), message="Thumbnail prompts not yet implemented")


@router.post("/{job_id}/thumbnail-upload", response_model=APIResponse)
async def upload_thumbnail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=model_to_video_job_out(job), message="Thumbnail upload not yet implemented")


@router.post("/{job_id}/thumbnail-skip", response_model=APIResponse)
async def skip_thumbnail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.thumbnail_status = "skipped"
    await db.commit()
    return APIResponse(data=model_to_video_job_out(job))
