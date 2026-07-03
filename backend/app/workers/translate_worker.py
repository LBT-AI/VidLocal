from celery import shared_task
import logging
from sqlalchemy import select

from app.config import settings
from app.models.project import Project
from app.models.subtitle_cue import SubtitleCue
from app.services.storage_service import storage
from app.services.gemini_service import gemini_service
from app.services.deeplx_translate_service import deeplx_translate_service
from app.services.cps_service import cps_service
from app.services.srt_service import srt_service, SRTCue
from app.database import get_async_session
from app.services.glossary_service import glossary_service

logger = logging.getLogger(__name__)
VALID_SUBTITLE_OUTPUT_MODES = {"translated", "bilingual", "original_plus_translated"}


@shared_task(bind=True, name="workers.translate_worker.translate")
def translate(
    self,
    project_id: str,
    provider: str | None = None,
    auto_fix_cps: bool = True,
    subtitle_output_mode: str | None = None,
):
    import asyncio
    asyncio.run(_translate_async(self, project_id, provider, auto_fix_cps, subtitle_output_mode))


async def _translate_async(
    task,
    project_id: str,
    provider: str | None,
    auto_fix_cps: bool,
    subtitle_output_mode: str | None,
):
    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        task.update_state(state="STARTED", meta={"progress": 10})
        cues_result = await db.execute(
            select(SubtitleCue).where(SubtitleCue.project_id == project_id).order_by(SubtitleCue.cue_index)
        )
        zh_cues = cues_result.scalars().all()
        if not zh_cues:
            raise ValueError("No Chinese cues found")
        srt_cues = [SRTCue(index=c.cue_index, start_ms=c.start_ms, end_ms=c.end_ms, text=c.zh_text or "") for c in zh_cues]
        provider = (provider or settings.TRANSLATE_PROVIDER).lower()
        subtitle_output_mode = subtitle_output_mode or settings.SUBTITLE_OUTPUT_MODE
        if subtitle_output_mode not in VALID_SUBTITLE_OUTPUT_MODES:
            raise ValueError(f"Invalid subtitle output mode: {subtitle_output_mode}")
        task.update_state(state="STARTED", meta={"progress": 30})
        glossary_entries = []
        try:
            glossary_entries = await glossary_service.get_glossary(project_id=project.id)
        except Exception as e:
            logger.warning("Failed to load glossary for project %s: %s", project_id, e)

        try:
            if provider == "gemini":
                translated = gemini_service.translate_cues(srt_cues, glossary_entries)
            elif provider == "deeplx":
                translated = await deeplx_translate_service.translate_cues(srt_cues, glossary_entries=glossary_entries)
            else:
                raise ValueError(f"Provider {provider} not implemented")
        except Exception as e:
            logger.exception("Translation failed project_id=%s provider=%s", project_id, provider)
            project.status = "error"
            await db.commit()
            raise RuntimeError(f"Translation failed: {str(e)}")
        task.update_state(state="STARTED", meta={"progress": 70})
        for i, cue in enumerate(translated):
            db_cue = zh_cues[i]
            db_cue.vi_text = cue.text
            cps_result = cps_service.check_cps(cue.text, cue.start_ms, cue.end_ms)
            db_cue.cps = cps_result["cps"]
            if provider == "gemini" and auto_fix_cps and cps_result["status"] != "ok":
                fixed = gemini_service.auto_fix_cps(cue)
                db_cue.vi_text = fixed.text
                cps_result = cps_service.check_cps(fixed.text, cue.start_ms, cue.end_ms)
                db_cue.cps = cps_result["cps"]
            db_cue.status = cps_result["status"]
        vi_srt_cues = [SRTCue(index=c.cue_index, start_ms=c.start_ms, end_ms=c.end_ms, text=c.vi_text or "") for c in zh_cues]
        vi_srt_content = srt_service.generate(vi_srt_cues)
        vi_srt_path = storage.save_file(project_id, vi_srt_content.encode("utf-8"), "vi.srt")
        metadata = project.metadata_json or {}
        metadata["translate_provider"] = provider
        metadata["subtitle_output_mode"] = subtitle_output_mode
        metadata["vi_srt_path"] = vi_srt_path

        if subtitle_output_mode == "bilingual":
            bilingual_content = srt_service.generate_bilingual(srt_cues, vi_srt_cues)
            bilingual_path = storage.save_file(project_id, bilingual_content.encode("utf-8"), "bilingual.srt")
            metadata["bilingual_srt_path"] = bilingual_path
        elif subtitle_output_mode == "original_plus_translated":
            zh_content = srt_service.generate(srt_cues)
            zh_alias_path = storage.save_file(project_id, zh_content.encode("utf-8"), "original.zh.srt")
            vi_alias_path = storage.save_file(project_id, vi_srt_content.encode("utf-8"), "translated.vi.srt")
            metadata["original_zh_srt_path"] = zh_alias_path
            metadata["translated_vi_srt_path"] = vi_alias_path

        project.vi_srt_path = vi_srt_path
        project.metadata_json = metadata
        project.status = "pending"
        await db.commit()
        task.update_state(state="SUCCESS", meta={"progress": 100})
        return {"status": "completed", "cues_count": len(translated), "subtitle_output_mode": subtitle_output_mode}
