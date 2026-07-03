import os
import asyncio
import logging
from celery import shared_task
from sqlalchemy import select, delete

from app.config import settings
from app.models.project import Project
from app.models.tts_segment import TTSSegment
from app.services.storage_service import storage
from app.services.ffmpeg_service import ffmpeg_service
from app.services.srt_service import srt_service, SRTCue
from app.database import get_async_session

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.tts_worker.generate_tts")
def generate_tts(self, project_id: str, voice: str | None = None):
    asyncio.run(_generate_tts_async(self, project_id, voice))


async def _generate_tts_async(task, project_id: str, voice: str | None):
    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        task.update_state(state="STARTED", meta={"progress": 10})
        try:
            if settings.TTS_PROVIDER != "edge-tts":
                raise ValueError(f"TTS provider {settings.TTS_PROVIDER} not implemented")

            voice = voice or settings.TTS_VOICE
            cues = _load_vi_srt_cues(project_id, project.vi_srt_path)
            if not cues:
                raise ValueError("Vietnamese SRT is empty or missing")

            project_dir = storage.get_project_dir(project_id)
            tts_dir = project_dir / "tts"
            tts_dir.mkdir(exist_ok=True)
            await db.execute(delete(TTSSegment).where(TTSSegment.project_id == project_id))

            total = len(cues)
            overflow_count = 0
            valid_segments = []

            for i, cue in enumerate(cues):
                if not cue.text.strip():
                    continue

                cue_duration_ms = cue.end_ms - cue.start_ms
                audio_path = str(tts_dir / f"cue_{cue.index:04d}.mp3")
                duration_ms = await _generate_synced_cue_audio(cue, voice, audio_path, tts_dir)
                sync_status = "ok"

                if duration_ms > cue_duration_ms * 1.05:
                    sync_status = "overflow"
                    overflow_count += 1

                db.add(
                    TTSSegment(
                        project_id=project_id,
                        cue_index=cue.index,
                        audio_path=audio_path,
                        duration_ms=int(duration_ms),
                        sync_status=sync_status,
                    )
                )
                valid_segments.append(
                    {
                        "path": audio_path,
                        "start_ms": cue.start_ms,
                        "end_ms": cue.end_ms,
                    }
                )
                progress = 10 + int(((i + 1) / total) * 75)
                task.update_state(state="STARTED", meta={"progress": progress})

            if not valid_segments:
                raise ValueError("No valid Vietnamese TTS segments generated")

            task.update_state(state="STARTED", meta={"progress": 90})
            mixed_path = str(project_dir / "vi_voice_mixed.wav")
            metadata = project.metadata_json or {}
            metadata_duration_ms = int((metadata.get("duration", 0) or 0) * 1000)
            srt_duration_ms = max(seg["end_ms"] for seg in valid_segments)
            total_duration_ms = max(metadata_duration_ms, srt_duration_ms)
            await ffmpeg_service.mix_tts_segments(valid_segments, mixed_path, total_duration_ms)
            metadata["tts_audio_path"] = mixed_path
            project.metadata_json = metadata
            project.audio_path = mixed_path
            project.status = "pending"
            await db.commit()
            task.update_state(state="SUCCESS", meta={"progress": 100})
            return {"status": "completed", "total_cues": total, "overflow_count": overflow_count, "audio_path": mixed_path}
        except Exception as e:
            logger.exception("TTS failed project_id=%s voice=%s", project_id, voice)
            await db.rollback()
            project.status = "error"
            await db.commit()
            raise RuntimeError(f"TTS failed: {str(e)}")


def _load_vi_srt_cues(project_id: str, vi_srt_path: str | None) -> list[SRTCue]:
    if vi_srt_path and os.path.exists(vi_srt_path):
        with open(vi_srt_path, "r", encoding="utf-8") as f:
            return srt_service.parse(f.read())
    content = storage.read_file(project_id, "vi.srt")
    return srt_service.parse(content.decode("utf-8"))


async def _generate_synced_cue_audio(cue: SRTCue, voice: str, audio_path: str, tts_dir) -> float:
    rates = [settings.TTS_RATE, "+15%", "+25%"]
    duration_ms = 0.0
    for idx, rate in enumerate(rates):
        candidate_path = audio_path if idx == 0 else str(tts_dir / f"cue_{cue.index:04d}_rate_{idx}.mp3")
        await _generate_edge_tts(cue.text, voice, candidate_path, rate=rate, volume=settings.TTS_VOLUME)
        duration_ms = await _get_audio_duration(candidate_path)
        if candidate_path != audio_path:
            os.replace(candidate_path, audio_path)
        if duration_ms <= (cue.end_ms - cue.start_ms) * 1.05:
            break
    return duration_ms


async def _generate_edge_tts(text: str, voice: str, output_path: str, rate: str = "+0%", volume: str = "+0%"):
    import edge_tts
    last_error = None
    for attempt in range(max(settings.TTS_RETRIES, 0) + 1):
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
            await asyncio.wait_for(communicate.save(output_path), timeout=settings.TTS_TIMEOUT_SECONDS)
            return
        except Exception as exc:
            last_error = exc
            logger.warning("Edge TTS attempt %s failed: %s", attempt + 1, exc)
            if attempt < settings.TTS_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Edge TTS failed after retries: {last_error}")


async def _get_audio_duration(audio_path: str) -> float:
    import subprocess
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
    return float(result.stdout.strip()) * 1000
