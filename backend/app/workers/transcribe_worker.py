import json
from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.models.project import Project
from app.models.subtitle_cue import SubtitleCue
from app.services.storage_service import storage
from app.services.whisper_service import whisper_service
from app.services.srt_service import srt_service
from app.database import get_async_session


@shared_task(bind=True, name="workers.transcribe_worker.transcribe")
def transcribe(self, project_id: str):
    import asyncio
    asyncio.run(_transcribe_async(self, project_id))


async def _transcribe_async(task, project_id: str):
    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        task.update_state(state="STARTED", meta={"progress": 10})
        try:
            transcription = whisper_service.transcribe(project.audio_path, project_id)
        except Exception as e:
            project.status = "error"
            await db.commit()
            raise RuntimeError(f"Transcription failed: {str(e)}")
        task.update_state(state="STARTED", meta={"progress": 60})
        srt_content = transcription["srt"]
        srt_bytes = srt_content.encode("utf-8")
        srt_path = storage.save_file(project_id, srt_bytes, "zh.srt")
        wt_bytes = json.dumps(transcription["word_timestamps"], ensure_ascii=False).encode("utf-8")
        storage.save_file(project_id, wt_bytes, "zh_word_timestamps.json")
        task.update_state(state="STARTED", meta={"progress": 80})
        for cue in transcription["cues"]:
            db_cue = SubtitleCue(
                project_id=project_id,
                cue_index=cue.index,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                zh_text=cue.text,
                vi_text=None,
                cps=None,
                status="ok"
            )
            db.add(db_cue)
        project.zh_srt_path = srt_path
        project.status = "pending"
        await db.commit()
        task.update_state(state="SUCCESS", meta={"progress": 100})
        return {"status": "completed", "cues_count": len(transcription["cues"])}
