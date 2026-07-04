import asyncio
import logging

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.database import dispose_engine, get_async_session
from app.models.video_job import VideoJob
from downloaders.douyin_downloader import DouyinDownloadError
from services.download_engine import download_video


logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.douyin_download_worker.process")
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

        job.source_platform = "douyin"
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
                cookies_file=settings.DOUYIN_COOKIES_FILE,
                proxy=settings.DOUYIN_PROXY,
                user_agent=settings.DOUYIN_USER_AGENT,
                timeout_seconds=settings.DOWNLOAD_TIMEOUT_SECONDS,
            )
            metadata = engine_result["meta"]
            job.video_id = metadata.get("video_id")
            job.resolved_url = metadata.get("resolved_url")
            job.normalized_url = metadata.get("normalized_url")
            job.file_path = engine_result.get("file_path")
            job.source_file_path = job.file_path
            job.status = "completed"
            job.progress = 100
            await db.commit()
            _update_state(task, progress=100)
            logger.info("Douyin job completed job_id=%s file_path=%s", job_id, job.file_path)
        except DouyinDownloadError as e:
            metadata = getattr(e, "metadata", {}) or {}
            job.video_id = metadata.get("video_id")
            job.resolved_url = metadata.get("resolved_url")
            job.normalized_url = metadata.get("normalized_url")
            job.status = "failed"
            job.progress = 0
            job.error_code = e.error_code
            job.error_message = str(e)
            await db.commit()
            await _send_telegram_error(job)
            logger.warning("Douyin job failed job_id=%s error_code=%s error=%s", job_id, e.error_code, e)
            raise RuntimeError(f"Douyin download failed: {e}") from e


def _update_state(task, **meta):
    if task:
        try:
            task.update_state(state="STARTED", meta=meta)
        except Exception:
            pass


async def _send_telegram_error(job: VideoJob):
    if not job.admin_chat_id:
        return
    try:
        from app.services.telegram_bot_service import telegram_bot

        if not telegram_bot.application:
            return
        
        msg = "Có thể video bị giới hạn hoặc cần cookie.\nVui lòng thử link khác hoặc cấu hình cookie."
        formatted_text = telegram_bot.format_premium_progress(job, msg)
        
        if job.telegram_message_id:
            await telegram_bot.application.bot.edit_message_text(
                chat_id=int(job.admin_chat_id),
                message_id=job.telegram_message_id,
                text=formatted_text,
                parse_mode=None,
            )
        else:
            sent_msg = await telegram_bot.application.bot.send_message(
                chat_id=int(job.admin_chat_id),
                text=formatted_text,
                parse_mode=None,
            )
            job.telegram_message_id = sent_msg.message_id
    except Exception:
        logger.warning("Failed to send Douyin Telegram error for job_id=%s", job.id, exc_info=True)
