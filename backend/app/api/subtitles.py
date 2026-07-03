import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.subtitle_cue import SubtitleCue
from app.schemas.subtitle import SubtitleCueOut, SubtitleCueUpdate, TranslateRequest, FixCPSRequest
from app.schemas.common import APIResponse, JobStatusResponse
from app.services.storage_service import storage
from app.services.srt_service import srt_service, SRTCue
from app.services.cps_service import cps_service
from app.workers.celery_app import celery_app
from app.config import settings

router = APIRouter()


@router.get("/{project_id}/zh-srt")
async def get_zh_srt(
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
    if not project.zh_srt_path:
        raise HTTPException(status_code=404, detail="Chinese SRT not found")
    try:
        content = storage.read_file(project_id, "zh.srt")
        return content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=404, detail="Chinese SRT file not found")


@router.get("/{project_id}/vi-srt")
async def get_vi_srt(
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
    if not project.vi_srt_path:
        raise HTTPException(status_code=404, detail="Vietnamese SRT not found")
    try:
        content = storage.read_file(project_id, "vi.srt")
        return content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=404, detail="Vietnamese SRT file not found")


@router.get("/{project_id}/bilingual-srt")
async def get_bilingual_srt(
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
    try:
        content = storage.read_file(project_id, "bilingual.srt")
        return content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=404, detail="Bilingual SRT file not found")


@router.get("/{project_id}/cues", response_model=APIResponse[List[SubtitleCueOut]])
async def get_cues(
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
    cues_result = await db.execute(
        select(SubtitleCue).where(SubtitleCue.project_id == project_id).order_by(SubtitleCue.cue_index)
    )
    cues = cues_result.scalars().all()
    return APIResponse(data=[SubtitleCueOut.model_validate(c) for c in cues])


@router.put("/{project_id}/cues/{cue_idx}", response_model=APIResponse[SubtitleCueOut])
async def update_cue(
    project_id: uuid.UUID,
    cue_idx: int,
    data: SubtitleCueUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    cue_result = await db.execute(
        select(SubtitleCue).where(SubtitleCue.project_id == project_id, SubtitleCue.cue_index == cue_idx)
    )
    cue = cue_result.scalar_one_or_none()
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")
    if data.start_ms is not None:
        cue.start_ms = data.start_ms
    if data.end_ms is not None:
        cue.end_ms = data.end_ms
    if data.zh_text is not None:
        cue.zh_text = data.zh_text
    if data.vi_text is not None:
        cue.vi_text = data.vi_text
        if cue.vi_text and cue.end_ms > cue.start_ms:
            cps_result = cps_service.check_cps(cue.vi_text, cue.start_ms, cue.end_ms)
            cue.cps = cps_result["cps"]
            cue.status = cps_result["status"]
    if data.status is not None:
        cue.status = data.status
    await db.commit()
    await db.refresh(cue)
    if data.vi_text is not None:
        await _regenerate_vi_srt(project_id, db)
    return APIResponse(data=SubtitleCueOut.model_validate(cue))


async def _regenerate_vi_srt(project_id: uuid.UUID, db: AsyncSession):
    cues_result = await db.execute(
        select(SubtitleCue).where(SubtitleCue.project_id == project_id).order_by(SubtitleCue.cue_index)
    )
    cues = cues_result.scalars().all()
    srt_cues = [
        SRTCue(index=c.cue_index, start_ms=c.start_ms, end_ms=c.end_ms, text=c.vi_text or "")
        for c in cues
    ]
    srt_content = srt_service.generate(srt_cues)
    storage.save_file(project_id, srt_content.encode("utf-8"), "vi.srt")
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one()
    project.vi_srt_path = str(storage.get_project_dir(project_id) / "vi.srt")
    await db.commit()


@router.post("/{project_id}/translate", response_model=APIResponse[JobStatusResponse])
async def queue_translate(
    project_id: uuid.UUID,
    data: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.zh_srt_path:
        raise HTTPException(status_code=400, detail="Chinese SRT not found. Transcribe first.")
    project.status = "translating"
    await db.commit()
    provider = data.provider or settings.TRANSLATE_PROVIDER
    subtitle_output_mode = data.subtitle_output_mode or settings.SUBTITLE_OUTPUT_MODE
    task = celery_app.send_task(
        "workers.translate_worker.translate",
        args=[str(project_id), provider, data.auto_fix_cps, subtitle_output_mode]
    )
    return APIResponse(data=JobStatusResponse(job_id=task.id, status="PENDING", progress=0.0), job_id=task.id)


@router.post("/{project_id}/fix-cps", response_model=APIResponse[dict])
async def fix_cps(
    project_id: uuid.UUID,
    data: FixCPSRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    from app.services.gemini_service import gemini_service
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    query = select(SubtitleCue).where(
        SubtitleCue.project_id == project_id,
        SubtitleCue.status.in_(["cps_warning", "needs_review"])
    )
    if data.cue_indices:
        query = query.where(SubtitleCue.cue_index.in_(data.cue_indices))
    cues_result = await db.execute(query.order_by(SubtitleCue.cue_index))
    cues = cues_result.scalars().all()
    fixed_count = 0
    for cue in cues:
        srt_cue = SRTCue(index=cue.cue_index, start_ms=cue.start_ms, end_ms=cue.end_ms, text=cue.vi_text or "")
        fixed = gemini_service.auto_fix_cps(srt_cue)
        cue.vi_text = fixed.text
        cps_result = cps_service.check_cps(fixed.text, cue.start_ms, cue.end_ms)
        cue.cps = cps_result["cps"]
        cue.status = cps_result["status"]
        fixed_count += 1
    await db.commit()
    await _regenerate_vi_srt(project_id, db)
    return APIResponse(data={"fixed_count": fixed_count})
