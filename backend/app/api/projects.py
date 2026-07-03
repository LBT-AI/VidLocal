import uuid
import shutil
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, BackgroundTasks
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models.project import Project
from app.models.subtitle_cue import SubtitleCue
from app.models.tts_segment import TTSSegment
from app.schemas.project import ProjectCreate, ProjectOut, ProjectListOut, ProjectUpdate
from app.schemas.common import APIResponse, JobStatusResponse
from app.services.storage_service import storage
from app.services.ffmpeg_service import ffmpeg_service, FFmpegError
from app.workers.celery_app import celery_app
from app.config import settings

router = APIRouter()


@router.post("", response_model=APIResponse[ProjectOut])
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    project = Project(
        user_id=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        title=data.title,
        source_url=data.source_url,
        status="pending"
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return APIResponse(data=ProjectOut.model_validate(project))


@router.get("", response_model=APIResponse[List[ProjectListOut]])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    if not user_id:
        return APIResponse(data=[])
    result = await db.execute(
        select(Project).where(Project.user_id == uuid.UUID(user_id)).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return APIResponse(data=[ProjectListOut.model_validate(p) for p in projects])


@router.get("/{project_id}", response_model=APIResponse[ProjectOut])
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse(data=ProjectOut.model_validate(project))


@router.delete("/{project_id}", response_model=APIResponse[dict])
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    storage.delete_project(project_id)
    await db.delete(project)
    await db.commit()
    return APIResponse(data={"deleted": True})


@router.post("/{project_id}/upload", response_model=APIResponse[ProjectOut])
async def upload_video(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type. Only MP4/MOV/AVI/WEBM allowed")
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE / 1024 / 1024 / 1024:.0f}GB")
    filename = "original.mp4"
    file_path = storage.save_upload(project_id, file.file, filename)
    try:
        metadata = await ffmpeg_service.get_metadata(file_path)
    except FFmpegError as e:
        raise HTTPException(status_code=400, detail=f"Failed to process video: {str(e)}")
    project_dir = storage.get_project_dir(project_id)
    audio_path = str(project_dir / "audio.wav")
    try:
        await ffmpeg_service.extract_audio(file_path, audio_path)
    except FFmpegError as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract audio: {str(e)}")
    project.original_video_path = file_path
    project.audio_path = audio_path
    project.metadata_json = metadata
    project.status = "pending"
    await db.commit()
    await db.refresh(project)
    return APIResponse(data=ProjectOut.model_validate(project))


@router.post("/{project_id}/import-url", response_model=APIResponse[ProjectOut])
async def import_from_url(
    project_id: uuid.UUID,
    url: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    import yt_dlp
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project_dir = storage.get_project_dir(project_id)
    output_path = str(project_dir / "original.mp4")
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_path,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", project.title)
            project.title = title
            project.source_url = url
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download from URL. Please upload manually. Error: {str(e)}")
    try:
        metadata = await ffmpeg_service.get_metadata(output_path)
    except FFmpegError as e:
        raise HTTPException(status_code=400, detail=f"Failed to process downloaded video: {str(e)}")
    audio_path = str(project_dir / "audio.wav")
    try:
        await ffmpeg_service.extract_audio(output_path, audio_path)
    except FFmpegError as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract audio: {str(e)}")
    project.original_video_path = output_path
    project.audio_path = audio_path
    project.metadata_json = metadata
    await db.commit()
    await db.refresh(project)
    return APIResponse(data=ProjectOut.model_validate(project))


@router.post("/{project_id}/transcribe", response_model=APIResponse[JobStatusResponse])
async def queue_transcribe(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == uuid.UUID(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.audio_path:
        raise HTTPException(status_code=400, detail="No audio found. Upload video first.")
    project.status = "transcribing"
    await db.commit()
    task = celery_app.send_task("workers.transcribe_worker.transcribe", args=[str(project_id)])
    return APIResponse(data=JobStatusResponse(job_id=task.id, status="PENDING", progress=0.0), job_id=task.id)
