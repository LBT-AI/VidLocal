import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select

from app.config import settings
from app.models.video_job import VideoJob
from app.database import get_async_session
from app.services.facebook_download_service import facebook_download_service, FacebookDownloadError
from app.services.video_understanding_service import video_understanding_service, VideoUnderstandingError
from app.services.seo_metadata_service import seo_metadata_service
from app.services.character_extraction_service import character_extraction_service
from app.models.character_glossary_draft import CharacterGlossaryItem
from app.services.youtube_upload_service import youtube_upload_service, YouTubeUploadError
from app.services.ffmpeg_service import ffmpeg_service, FFmpegError
from app.services.storage_cleanup_service import storage_cleanup
from app.services.telegram_bot_service import telegram_bot

logger = logging.getLogger(__name__)


class FacebookToYouTubeFlow:
    JOB_TYPE = "facebook_to_youtube"
    STORAGE_PREFIX = "facebook_downloads"

    def __init__(self, task=None):
        self.task = task

    def _send_telegram_update_sync(self, job, text, parse_mode="HTML"):
        """Synchronous wrapper for Telegram updates from Celery task."""
        if job.admin_chat_id and telegram_bot.application:
            import asyncio
            try:
                chat_id = int(job.admin_chat_id)
                bot = telegram_bot.application.bot
                if job.telegram_message_id:
                    asyncio.get_event_loop().run_coroutine_threadsafe(
                        bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=job.telegram_message_id,
                            text=text,
                            parse_mode=parse_mode,
                        ),
                        asyncio.get_event_loop(),
                    )
                else:
                    future = asyncio.run_coroutine_threadsafe(
                        bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode),
                        asyncio.get_event_loop(),
                    )
                    msg = future.result()
                    job.telegram_message_id = msg.message_id
            except Exception as e:
                logger.warning("Failed to send TG update: %s", e)

    async def _send_telegram(self, job, text, parse_mode="HTML"):
        if job.admin_chat_id and telegram_bot.application:
            try:
                chat_id = int(job.admin_chat_id)
                bot = telegram_bot.application.bot
                if job.telegram_message_id:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=job.telegram_message_id,
                        text=text,
                        parse_mode=parse_mode,
                    )
                else:
                    msg = await bot.send_message(
                        chat_id=chat_id, text=text, parse_mode=parse_mode
                    )
                    job.telegram_message_id = msg.message_id
            except Exception as e:
                logger.warning("Failed to send TG update: %s", e)

    async def _send_preview(self, job):
        if job.admin_chat_id and telegram_bot.application:
            try:
                await telegram_bot._send_preview(int(job.admin_chat_id), str(job.id))
            except Exception as e:
                logger.warning("Failed to send preview: %s", e)

    def _update_state(self, **meta):
        if self.task:
            try:
                self.task.update_state(state="STARTED", meta=meta)
            except Exception:
                pass

    async def run_process(self, job_id: str):
        async_session = get_async_session()
        async with async_session() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise ValueError(f"VideoJob {job_id} not found")

            job_dir = os.path.join(
                settings.PROJECT_DATA_DIR, self.STORAGE_PREFIX, str(job.id)
            )
            source_path = os.path.join(job_dir, "source.mp4")
            os.makedirs(job_dir, exist_ok=True)

            job.temp_dir = job_dir
            job.source_file_path = source_path

            try:
                # 1. Download
                job.status = "downloading"
                await db.commit()
                await self._send_telegram(job, "📥 Đang tải video từ Facebook...")
                self._update_state(progress=10)
                fb_meta = await facebook_download_service.download_with_metadata(
                    job.source_url, job_dir
                )
                job.source_file_path = source_path
                job.status = "downloaded"
                job.progress = 25
                await db.commit()

                await storage_cleanup.backup_to_r2(job, source_path)
                if job.r2_key:
                    await db.commit()

                await self._send_telegram(
                    job, "✅ Đã tải video.\n🎙 Đang trích xuất nội dung..."
                )

                # 2. Transcribe
                job.status = "transcribing"
                await db.commit()
                self._update_state(progress=40)
                try:
                    understanding = await video_understanding_service.understand(
                        source_path, job_dir
                    )
                    transcript = understanding["transcript"]
                    transcript_lang = understanding["language"]
                except (VideoUnderstandingError, Exception) as e:
                    logger.warning("Transcription failed for job %s: %s", job_id, e)
                    transcript = ""
                    transcript_lang = "unknown"
                    await self._send_telegram(
                        job,
                        "⚠️ Không thể trích xuất nội dung. Dùng metadata gốc.",
                    )

                job.transcript = transcript
                job.transcript_language = transcript_lang
                job.progress = 55
                await db.commit()

                # 3. Character extraction (if glossary enabled)
                job.glossary_status = "pending"
                job.status = "extracting_characters"
                job.progress = 65
                await db.commit()
                self._update_state(progress=65)
                glossary_items_for_meta = []
                if transcript and transcript.strip() and settings.GLOSSARY_ENABLED:
                    try:
                        await self._send_telegram(job, "🔍 Đang phân tích nhân vật...")
                        extraction_data = character_extraction_service.extract(transcript)
                        draft, items = await character_extraction_service.save_draft(
                            job.id, extraction_data
                        )
                        job.glossary_draft_id = draft.id
                        await db.commit()
                        if items:
                            await telegram_bot._send_glossary_review(job.id)
                            job.status = "awaiting_glossary"
                            job.progress = 70
                            await db.commit()
                            self._update_state(progress=70)
                            logger.info("Job %s awaiting glossary review", job_id)
                            return
                        else:
                            glossary_items_for_meta = items
                            job.glossary_status = "approved"
                    except Exception as e:
                        logger.warning("Character extraction failed for job %s: %s", job_id, e)

                # Continue directly if no glossary items need review
                source_metadata = {
                    "title": fb_meta.get("title", ""),
                    "description": fb_meta.get("description", ""),
                    "uploader": fb_meta.get("uploader", ""),
                }
                await self._run_after_glossary(source_metadata, job_id)

            except FacebookDownloadError as e:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
                await self._send_telegram(job, f"❌ Lỗi tải video: {e}")
                raise RuntimeError(f"Download failed: {e}")
            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
                await self._send_telegram(job, f"❌ Lỗi xử lý: {e}")
                logger.exception("Facebook process failed job_id=%s", job_id)
                raise

    async def _run_after_glossary(self, source_metadata: dict, job_id: str):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            transcript = job.transcript or ""
            glossary_items = []
            if job.glossary_status == "approved" and job.glossary_draft_id:
                items_result = await db.execute(
                    select(CharacterGlossaryItem)
                    .where(
                        CharacterGlossaryItem.draft_id == job.glossary_draft_id,
                        CharacterGlossaryItem.approved.is_(True),
                    )
                    .order_by(CharacterGlossaryItem.source_name)
                )
                glossary_items = list(items_result.scalars().all())
            job.status = "metadata_generating"
            job.progress = 75
            await db.commit()

        import json as json_mod
        if transcript and transcript.strip():
            meta = seo_metadata_service.generate(transcript, source_metadata, glossary_items)
        else:
            logger.info("Empty transcript for job %s, safe metadata", job_id)
            meta = seo_metadata_service.generate(
                "Nội dung video từ Facebook. " + source_metadata.get("title", ""),
                source_metadata,
                glossary_items,
            )
            if not meta.get("risk_flags"):
                meta["risk_flags"] = ["reup"]

        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            job.ai_title = meta["title"][:90]
            job.ai_description = meta["description"]
            job.ai_tags = json_mod.dumps(meta["tags"], ensure_ascii=False)
            job.ai_hashtags = json_mod.dumps(meta["hashtags"], ensure_ascii=False)
            job.ai_summary = meta["summary"]
            job.ai_hook = meta["hook"]
            job.ai_category = meta["category"]
            job.risk_flags = json_mod.dumps(meta["risk_flags"], ensure_ascii=False)
            job.metadata_status = "generated"
            job.status = "waiting_approval"
            job.progress = 85
            await db.commit()
            self._update_state(progress=85)

        await self._send_preview(job)
        logger.info("Job %s awaiting admin approval", job_id)

    async def run_process_after_glossary(self, job_id: str):
        await self._run_after_glossary({}, job_id)

    async def run_upload(self, job_id: str):
        async_session = get_async_session()
        async with async_session() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise ValueError(f"VideoJob {job_id} not found")

            job_dir = job.temp_dir or os.path.join(
                settings.PROJECT_DATA_DIR, self.STORAGE_PREFIX, str(job.id)
            )
            source_path = os.path.join(job_dir, "source.mp4")
            normalized_path = os.path.join(job_dir, "normalized.mp4")
            watermarked_path = os.path.join(job_dir, "watermarked.mp4")
            clean_up = False

            try:
                # 1. Normalize
                job.status = "processing"
                job.progress = 10
                await db.commit()
                await self._send_telegram(job, "🔄 Đang xử lý video...")
                self._update_state(progress=10)

                input_path = source_path
                if not os.path.exists(input_path):
                    input_path = job.source_file_path or source_path
                if not os.path.exists(input_path):
                    raise FileNotFoundError(f"Source file not found: {input_path}")

                await ffmpeg_service.normalize_for_youtube(input_path, normalized_path)
                job.progress = 30
                await db.commit()

                # 2. Watermark
                from app.services.video_watermark_service import video_watermark, WatermarkError
                job.status = "watermarking"
                await db.commit()
                await self._send_telegram(job, "💧 Đang thêm watermark...")
                try:
                    await video_watermark.add_watermark(
                        normalized_path, watermarked_path
                    )
                    job.watermarked_file_path = watermarked_path
                    upload_path = watermarked_path
                except (WatermarkError, Exception) as e:
                    logger.warning("Watermark failed, using normalized: %s", e)
                    upload_path = normalized_path

                job.progress = 50
                await db.commit()

                # 3. Upload YouTube
                job.status = "uploading_youtube"
                await db.commit()
                await self._send_telegram(job, "📤 Đang upload lên YouTube...")
                self._update_state(progress=60)

                tags = []
                if job.ai_tags:
                    try:
                        tags = json.loads(job.ai_tags)
                    except (json.JSONDecodeError, TypeError):
                        tags = []

                result = youtube_upload_service.upload_video(
                    file_path=upload_path,
                    title=job.ai_title or "Video từ Facebook",
                    description=job.ai_description or "",
                    tags=tags,
                    privacy="private",
                    category=job.ai_category or "",
                )
                job.youtube_video_id = result["video_id"]
                job.youtube_url = result["url"]

                # 4. Set thumbnail if available
                if job.thumbnail_path and os.path.exists(job.thumbnail_path):
                    try:
                        youtube_upload_service.set_thumbnail(result["video_id"], job.thumbnail_path)
                        logger.info("Thumbnail set for video %s", result["video_id"])
                    except Exception as e:
                        logger.warning("Failed to set thumbnail for job %s: %s", job_id, e)

                job.status = "completed"
                job.progress = 100
                await db.commit()
                self._update_state(progress=100)
                clean_up = True

                await self._send_telegram(
                    job,
                    f"✅ <b>Upload thành công!</b>\n"
                    f"📹 <a href='{result['url']}'>Xem trên YouTube</a>\n"
                    f"🔒 Chế độ: private",
                )
                logger.info("Upload OK for job %s: %s", job_id, result["url"])

            except (YouTubeUploadError, FFmpegError, FileNotFoundError) as e:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
                await self._send_telegram(
                    job,
                    f"❌ Lỗi upload: {e}\n"
                    f"🆔 Job: <code>{job_id}</code>\n"
                    f"💾 File tạm giữ lại để retry/debug.",
                )
                logger.error("Upload failed for job %s", job_id)
                raise RuntimeError(f"Upload failed: {e}")
            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
                await self._send_telegram(job, f"❌ Lỗi không xác định: {e}")
                logger.exception("Upload failed for job_id=%s", job_id)
                raise
            finally:
                if clean_up:
                    await storage_cleanup.cleanup_job_files(job)
