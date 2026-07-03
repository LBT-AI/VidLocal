import os
import logging
from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.models.project import Project
from app.services.ffmpeg_service import ffmpeg_service, FFmpegError
from app.database import get_async_session

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.render_worker.render")
def render(self, project_id: str, mode: str = "hardsub"):
    import asyncio
    asyncio.run(_render_async(self, project_id, mode))


async def _render_async(task, project_id: str, mode: str):
    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        task.update_state(state="STARTED", meta={"progress": 20})
        try:
            original_video = project.original_video_path
            subtitle_path = _select_subtitle_path(project)
            mixed_audio = _select_tts_audio_path(project)
            if not original_video or not os.path.exists(original_video):
                raise ValueError("Original video not found")
            project_dir = os.path.dirname(original_video)
            if not mixed_audio or not os.path.exists(mixed_audio):
                raise ValueError("Vietnamese TTS audio not found. Generate TTS first.")
            if mode != "voice_only" and (not subtitle_path or not os.path.exists(subtitle_path)):
                raise ValueError("Subtitle file not found")
            if mode == "voice_only":
                output_path = os.path.join(project_dir, "output_voice.mp4")
                await ffmpeg_service.render_voice_only(original_video, mixed_audio, output_path)
            elif mode == "softsub":
                output_path = os.path.join(project_dir, "output_soft_sub.mp4")
                await ffmpeg_service.render_softsub(original_video, mixed_audio, subtitle_path, output_path)
            elif mode == "hardsub":
                output_path = os.path.join(project_dir, "output_hardsub.mp4")
                await ffmpeg_service.render_hardsub(original_video, mixed_audio, subtitle_path, output_path)
            else:
                raise ValueError(f"Unknown render mode: {mode}")
            task.update_state(state="STARTED", meta={"progress": 80})
            project.final_video_path = output_path
            project.status = "done"
            await db.commit()
            task.update_state(state="SUCCESS", meta={"progress": 100})
            return {"status": "completed", "mode": mode, "output_path": output_path}
        except Exception as e:
            logger.exception("Render failed project_id=%s mode=%s", project_id, mode)
            await db.rollback()
            project.status = "error"
            await db.commit()
            raise RuntimeError(f"Render failed: {str(e)}")


def _select_tts_audio_path(project: Project) -> str | None:
    metadata = project.metadata_json or {}
    tts_audio_path = metadata.get("tts_audio_path")
    if tts_audio_path:
        return tts_audio_path
    if project.audio_path and os.path.basename(project.audio_path).startswith("vi_voice_mixed"):
        return project.audio_path
    return None


def _select_subtitle_path(project: Project) -> str | None:
    metadata = project.metadata_json or {}
    if metadata.get("subtitle_output_mode") == "bilingual" and metadata.get("bilingual_srt_path"):
        return metadata["bilingual_srt_path"]
    return project.vi_srt_path
