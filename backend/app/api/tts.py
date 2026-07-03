import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.tts_segment import TTSSegment
from app.schemas.common import APIResponse, JobStatusResponse
from app.workers.celery_app import celery_app
from app.config import settings

router = APIRouter()


@router.post("/{project_id}/tts", response_model=APIResponse[JobStatusResponse])
async def queue_tts(
    project_id: uuid.UUID,
    voice: str | None = None,
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
        raise HTTPException(status_code=400, detail="Vietnamese SRT not found. Translate first.")
    project.status = "tts"
    await db.commit()
    selected_voice = voice or settings.TTS_VOICE
    task = celery_app.send_task("workers.tts_worker.generate_tts", args=[str(project_id), selected_voice])
    return APIResponse(data=JobStatusResponse(job_id=task.id, status="PENDING", progress=0.0), job_id=task.id)


@router.get("/{project_id}/tts/{cue_idx}")
async def get_tts_audio(
    project_id: uuid.UUID,
    cue_idx: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tts_result = await db.execute(
        select(TTSSegment).where(TTSSegment.project_id == project_id, TTSSegment.cue_index == cue_idx)
    )
    tts = tts_result.scalar_one_or_none()
    if not tts or not tts.audio_path:
        raise HTTPException(status_code=404, detail="TTS audio not found")
    return FileResponse(tts.audio_path, media_type="audio/mpeg")
