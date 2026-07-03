import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.publish_job import PublishJob
from app.schemas.common import APIResponse, JobStatusResponse
from app.workers.celery_app import celery_app

router = APIRouter()


@router.post("/{project_id}/render", response_model=APIResponse[JobStatusResponse])
async def queue_render(
    project_id: uuid.UUID,
    mode: str = "hardsub",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.vi_srt_path:
        raise HTTPException(status_code=400, detail="Vietnamese SRT not found")
    project.status = "rendering"
    await db.commit()
    task = celery_app.send_task("workers.render_worker.render", args=[str(project_id), mode])
    return APIResponse(data=JobStatusResponse(job_id=task.id, status="PENDING", progress=0.0), job_id=task.id)


@router.get("/{project_id}/output")
async def download_output(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.final_video_path:
        raise HTTPException(status_code=404, detail="Final video not ready")
    return FileResponse(project.final_video_path, media_type="video/mp4", filename=f"{project.title}_localized.mp4")


@router.post("/{project_id}/publish", response_model=APIResponse[JobStatusResponse])
async def create_publish_job(
    project_id: uuid.UUID,
    platform: str,
    title: str,
    description: str = "",
    tags: List[str] = None,
    privacy: str = "private",
    scheduled_at: datetime = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.final_video_path:
        raise HTTPException(status_code=400, detail="Render video first")
    job = PublishJob(
        project_id=project_id,
        platform=platform,
        title=title,
        description=description,
        tags=tags or [],
        privacy=privacy,
        scheduled_at=scheduled_at,
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return APIResponse(data=JobStatusResponse(job_id=str(job.id), status="PENDING", progress=0.0), job_id=str(job.id))


@router.get("/{project_id}/publish-jobs", response_model=APIResponse[List[dict]])
async def list_publish_jobs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(PublishJob).where(PublishJob.project_id == project_id).order_by(PublishJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return APIResponse(data=[
        {
            "id": str(j.id),
            "platform": j.platform,
            "status": j.status,
            "privacy": j.privacy,
            "published_url": j.published_url,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat() if j.created_at else None
        }
        for j in jobs
    ])
