import asyncio
import logging

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.database import dispose_engine, get_async_session
from app.models.video_job import VideoJob
from downloaders.bilibili_downloader import BilibiliDownloadError
from services.download_engine import download_video


logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.bilibili_download_worker.process")
def process(self, job_id: str):
    dispose_engine()
    try:
        asyncio.run(_run(job_id, task=self))
    finally:
        dispose_engine()


async def _run(job_id: str, task=None):
    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"VideoJob {job_id} not found")

        job.status = "downloading"
        job.progress = 10
        job.error_message = None
        job.error_code = None
        await db.commit()
        _update_state(task, progress=10)

        try:
            engine_result = await download_video(
                job.source_url,
                output_dir="/app/data/downloads",
                cookies_file=settings.BILIBILI_COOKIES_FILE,
            )
            download_result = engine_result["meta"]
            job.source_platform = "bilibili"
            job.video_id = download_result.get("video_id")
            job.resolved_url = download_result.get("resolved_url")
            job.normalized_url = download_result.get("normalized_url")
            job.file_path = engine_result.get("file_path")
            job.source_file_path = job.file_path
            job.status = "completed"
            job.progress = 100
            await db.commit()
            _update_state(task, progress=100)
            logger.info("Bilibili job completed job_id=%s file_path=%s", job_id, job.file_path)
        except BilibiliDownloadError as e:
            metadata = getattr(e, "metadata", {}) or {}
            job.source_platform = "bilibili"
            job.video_id = metadata.get("video_id")
            job.resolved_url = metadata.get("resolved_url")
            job.normalized_url = metadata.get("normalized_url")
            job.status = "failed"
            job.progress = 0
            job.error_code = e.error_code
            job.error_message = str(e)
            await db.commit()
            logger.warning("Bilibili job failed job_id=%s error_code=%s error=%s", job_id, e.error_code, e)
            raise RuntimeError(f"Bilibili download failed: {e}") from e


def _update_state(task, **meta):
    if task:
        try:
            task.update_state(state="STARTED", meta=meta)
        except Exception:
            pass
