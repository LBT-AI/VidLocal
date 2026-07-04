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
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    video_id: Optional[str] = None
    resolved_url: Optional[str] = None
    normalized_url: Optional[str] = None
    file_path: Optional[str] = None
    updated_at: Optional[str] = None
    current_step: str = "download"
    steps: Optional[dict] = None
    transcript: Optional[str] = None
    glossary: Optional[List[dict]] = None
    metadata: Optional[dict] = None
    files: List[dict] = []
    logs: List[dict] = []
    options: Optional[dict] = None
    thumbnail: Optional[dict] = None
    transcript_srt_path: Optional[str] = None
    transcript_text_path: Optional[str] = None
    transcript_review_status: Optional[str] = None
    reviewed_at: Optional[str] = None

    class Config:
        from_attributes = True


class GlossaryItemOut(BaseModel):
    id: str
    category: str
    source_name: str
    target_name: str
    pronoun_style: Optional[str] = None
    family_clan: Optional[str] = None
    role: Optional[str] = None
    approved: bool

    class Config:
        from_attributes = True


class GlossaryItemUpsert(BaseModel):
    id: Optional[str] = None
    category: str = "character"
    source_name: str
    target_name: str
    pronoun_style: Optional[str] = None
    family_clan: Optional[str] = None
    role: Optional[str] = None
    approved: bool = True


def model_to_video_job_out(job: VideoJob) -> VideoJobOut:
    platform = job.source_platform or "facebook"
    current_step = job.current_step or "download"
    progress = job.progress or 0

    all_steps = ["download", "transcribe", "character_extract", "glossary_review", "seo_metadata", "watermark", "upload"]
    steps = {}
    try:
        current_idx = all_steps.index(current_step)
    except ValueError:
        current_idx = 0

    for idx, step_name in enumerate(all_steps):
        if job.status == "failed" and step_name == current_step:
            step_status = "failed"
            step_progress = job.stage_progress or 0
        elif job.status == "completed":
            step_status = "completed"
            step_progress = 100
        elif idx < current_idx:
            step_status = "completed"
            step_progress = 100
        elif idx > current_idx:
            step_status = "pending"
            step_progress = 0
        else: # idx == current_idx
            if job.status == "waiting_review":
                step_status = "waiting_review"
            else:
                step_status = "running"
            step_progress = job.stage_progress or 0
            
        steps[step_name] = {
            "status": step_status,
            "progress": step_progress
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
        error_message=job.error_message,
        error_code=job.error_code,
        video_id=job.video_id,
        resolved_url=job.resolved_url,
        normalized_url=job.normalized_url,
        file_path=job.file_path or job.source_file_path,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
        current_step=current_step,
        steps=steps,
        transcript=job.transcript,
        glossary=glossary,
        metadata=metadata,
        thumbnail=thumbnail,
        transcript_srt_path=job.transcript_srt_path,
        transcript_text_path=job.transcript_text_path,
        transcript_review_status=job.transcript_review_status,
        reviewed_at=job.reviewed_at.isoformat() if job.reviewed_at else None,
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
    from services.download_engine import detect_platform

    try:
        platform = detect_platform(data.url)
    except ValueError:
        platform = data.platform

    task_map = {
        "facebook": "workers.facebook_to_youtube_worker.process",
        "tiktok": "workers.tiktok_to_youtube_worker.process",
        "bilibili": "workers.bilibili_download_worker.process",
        "douyin": "workers.douyin_download_worker.process",
    }

    if platform == "facebook":
        from app.services.facebook_download_service import facebook_download_service
        if not facebook_download_service.validate_url(data.url):
            raise HTTPException(status_code=400, detail="Invalid Facebook URL")
    if platform not in task_map:
        raise HTTPException(status_code=400, detail="Unsupported platform. Use 'facebook', 'tiktok', 'bilibili', or 'douyin'")
    task_name = task_map[platform]

    title = data.title or data.url.split("/")[-1] or "Untitled"
    job = VideoJob(
        type=f"{platform}_download" if platform in ("bilibili", "douyin") else f"{platform}_to_youtube",
        source_url=data.url,
        source_platform=platform,
        target_platform="local" if platform in ("bilibili", "douyin") else "youtube",
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
    job.status = "running"
    job.current_step = "seo_metadata"
    job.review_state = "none"
    job.stage_progress = 0
    job.progress = 75
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
    job.status = "running"
    job.current_step = "seo_metadata"
    job.review_state = "none"
    job.stage_progress = 0
    job.progress = 75
    await db.commit()

    task_name = f"workers.{job.source_platform}_to_youtube_worker.process_after_glossary"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job))


@router.get("/{job_id}/glossary", response_model=List[GlossaryItemOut])
async def get_glossary(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    items_result = await db.execute(
        select(CharacterGlossaryItem)
        .where(CharacterGlossaryItem.job_id == job_id)
        .order_by(CharacterGlossaryItem.category, CharacterGlossaryItem.source_name)
    )
    items = items_result.scalars().all()
    return items


@router.post("/{job_id}/glossary/item", response_model=APIResponse)
async def upsert_glossary_item(
    job_id: uuid.UUID,
    item_in: GlossaryItemUpsert,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if item_in.id:
        item_uuid = uuid.UUID(item_in.id)
        item_result = await db.execute(
            select(CharacterGlossaryItem).where(CharacterGlossaryItem.id == item_uuid)
        )
        item = item_result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Glossary item not found")
    else:
        item = CharacterGlossaryItem(
            job_id=job.id,
            draft_id=job.glossary_draft_id,
        )
        db.add(item)
        
    item.category = item_in.category
    item.source_name = item_in.source_name
    item.target_name = item_in.target_name
    item.pronoun_style = item_in.pronoun_style
    item.family_clan = item_in.family_clan
    item.role = item_in.role
    item.approved = item_in.approved
    
    await db.commit()
    return APIResponse(success=True, message="Glossary item updated successfully")


@router.delete("/{job_id}/glossary/item/{item_id}", response_model=APIResponse)
async def delete_glossary_item(
    job_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    item_result = await db.execute(
        select(CharacterGlossaryItem).where(CharacterGlossaryItem.id == item_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Glossary item not found")
        
    await db.delete(item)
    await db.commit()
    return APIResponse(success=True, message="Glossary item deleted successfully")


@router.post("/{job_id}/approve-srt", response_model=APIResponse)
async def approve_srt(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.transcript_review_status = "approved"
    job.reviewed_at = datetime.utcnow()
    await db.commit()

    task_name = f"workers.{job.source_platform}_to_youtube_worker.process_after_srt"
    celery_app.send_task(task_name, args=[str(job.id)])

    return APIResponse(data=model_to_video_job_out(job))


@router.post("/{job_id}/retry-srt", response_model=APIResponse)
async def retry_srt(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Run transcribe only Celery task
    task_name = f"workers.{job.source_platform}_to_youtube_worker.retry_transcribe"
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
    if job.status != "waiting_review" or job.review_state != "waiting_upload":
        raise HTTPException(status_code=400, detail="Job is not waiting for upload approval")
    
    job.status = "running"
    job.current_step = "watermark"
    job.review_state = "none"
    job.stage_progress = 0
    job.progress = 90
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
    job.current_step = "download"
    job.review_state = "none"
    job.stage_progress = 0
    job.error_message = None
    job.error_code = None
    job.video_id = None
    job.resolved_url = None
    job.normalized_url = None
    job.file_path = None
    job.source_file_path = None
    job.progress = 0
    await db.commit()

    task_map = {
        "facebook": "workers.facebook_to_youtube_worker.process",
        "tiktok": "workers.tiktok_to_youtube_worker.process",
        "bilibili": "workers.bilibili_download_worker.process",
        "douyin": "workers.douyin_download_worker.process",
    }
    task_name = task_map.get(job.source_platform)
    if not task_name:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {job.source_platform}")
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
