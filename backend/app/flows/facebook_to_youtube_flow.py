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
from app.services.ytdlp_download import cleanup_partial_files
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
                
                formatted_text = telegram_bot.format_premium_progress(job, text)
                
                if job.telegram_message_id:
                    asyncio.get_event_loop().run_coroutine_threadsafe(
                        bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=job.telegram_message_id,
                            text=formatted_text,
                            parse_mode=None,
                        ),
                        asyncio.get_event_loop(),
                    )
                else:
                    future = asyncio.run_coroutine_threadsafe(
                        bot.send_message(chat_id=chat_id, text=formatted_text, parse_mode=None),
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
                
                formatted_text = telegram_bot.format_premium_progress(job, text)
                
                if job.telegram_message_id:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=job.telegram_message_id,
                        text=formatted_text,
                        parse_mode=None,
                    )
                else:
                    msg = await bot.send_message(
                        chat_id=chat_id, text=formatted_text, parse_mode=None
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
                job.status = "running"
                job.current_step = "download"
                job.review_state = "none"
                job.stage_progress = 10
                job.progress = 10
                await db.commit()
                await self._send_telegram(job, "📥 Đang tải video từ Facebook...")
                self._update_state(progress=10)
                fb_meta = await facebook_download_service.download_with_metadata(
                    job.source_url, job_dir
                )
                job.video_id = fb_meta.get("video_id")
                job.resolved_url = fb_meta.get("resolved_url")
                job.normalized_url = fb_meta.get("normalized_url")
                source_path = fb_meta.get("filepath") or source_path
                job.source_file_path = source_path
                job.status = "running"
                job.current_step = "transcribe"
                job.review_state = "none"
                job.stage_progress = 0
                job.progress = 25
                await db.commit()

                await storage_cleanup.backup_to_r2(job, source_path)
                if job.r2_key:
                    await db.commit()

                await self._send_telegram(
                    job, "✅ Đã tải video.\n🎙 Đang trích xuất nội dung..."
                )

                # 2. Transcribe
                job.status = "running"
                job.current_step = "transcribe"
                job.review_state = "none"
                job.stage_progress = 40
                job.progress = 40
                await db.commit()
                self._update_state(progress=40)
                try:
                    understanding = await video_understanding_service.understand(
                        source_path, job_dir
                    )
                    transcript = understanding["transcript"]
                    transcript_lang = understanding["language"]
                    srt_content = understanding.get("srt_content", "")
                except (VideoUnderstandingError, Exception) as e:
                    logger.warning("Transcription failed for job %s: %s", job_id, e)
                    job.status = "failed"
                    job.error_code = "transcription_failed"
                    job.error_message = str(e)
                    await db.commit()
                    await self._send_telegram(
                        job,
                        f"❌ Lỗi Speech-to-Text: {e}\nBạn có thể chọn Thử lại riêng bước này.",
                    )
                    raise RuntimeError(f"Transcription failed: {e}")

                if not transcript or not transcript.strip():
                    job.status = "failed"
                    job.error_code = "transcription_failed"
                    job.error_message = "Transcription produced empty text"
                    await db.commit()
                    await self._send_telegram(
                        job,
                        "❌ Lỗi Speech-to-Text: Phụ đề trống (không phát hiện được giọng nói).",
                    )
                    raise RuntimeError("Transcription produced empty text")

                # Save raw.srt and raw.txt
                srt_path = os.path.join(job_dir, "raw.srt")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                
                text_path = os.path.join(job_dir, "raw.txt")
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(transcript)

                job.transcript = transcript
                job.transcript_language = transcript_lang
                job.transcript_srt_path = srt_path
                job.transcript_text_path = text_path
                job.transcript_review_status = "pending"
                job.status = "waiting_review"
                job.current_step = "transcribe"
                job.review_state = "waiting_srt"
                job.stage_progress = 100
                job.progress = 50
                await db.commit()
                
                await self._send_telegram(
                    job, "📝 Đã hoàn thành Speech-to-Text. Chờ duyệt phụ đề..."
                )
                await telegram_bot._send_srt_review(job.id)
                return

            except FacebookDownloadError as e:
                cleanup_partial_files(job_dir)
                metadata = getattr(e, "metadata", {}) or {}
                job.video_id = metadata.get("video_id")
                job.resolved_url = metadata.get("resolved_url")
                job.normalized_url = metadata.get("normalized_url")
                job.status = "failed"
                job.error_message = str(e)
                job.error_code = getattr(e, "error_code", None)
                if job.source_file_path and not os.path.exists(job.source_file_path):
                    job.source_file_path = None
                await db.commit()
                if job.error_code == "facebook_no_formats":
                    await self._send_telegram(
                        job,
                        "❌ Link Facebook này không tải được. Hãy thử link video/reel gốc hoặc thêm cookies Facebook.",
                    )
                else:
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
            job.status = "running"
            job.current_step = "seo_metadata"
            job.review_state = "none"
            job.stage_progress = 0
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
            job.status = "waiting_review"
            job.current_step = "seo_metadata"
            job.review_state = "waiting_upload"
            job.stage_progress = 100
            job.progress = 85
            await db.commit()
            self._update_state(progress=85)

        await self._send_preview(job)
        logger.info("Job %s awaiting admin approval", job_id)

    async def run_process_after_srt(self, job_id: str):
        async_session = get_async_session()
        async with async_session() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return

            transcript = job.transcript or ""
            job.transcript_review_status = "approved"
            job.reviewed_at = datetime.now(timezone.utc)
            
            # 3. Character extraction (if glossary enabled)
            job.glossary_status = "pending"
            job.status = "running"
            job.current_step = "character_extract"
            job.review_state = "none"
            job.stage_progress = 0
            job.progress = 55
            await db.commit()

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
                        job.status = "waiting_review"
                        job.current_step = "character_extract"
                        job.review_state = "waiting_glossary"
                        job.stage_progress = 100
                        job.progress = 70
                        await db.commit()
                        logger.info("Job %s awaiting glossary review", job_id)
                        return
                    else:
                        job.glossary_status = "approved"
                except Exception as e:
                    logger.warning("Character extraction failed for job %s: %s", job_id, e)

            # Continue directly if no glossary items need review
            source_metadata = {
                "title": job.source_url.split("/")[-1] if job.source_url else "Untitled",
                "description": "",
                "uploader": "",
            }
            await self._run_after_glossary(source_metadata, job_id)

    async def run_transcribe_only(self, job_id: str):
        async_session = get_async_session()
        async with async_session() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            
            job_dir = job.temp_dir or os.path.join(
                settings.PROJECT_DATA_DIR, self.STORAGE_PREFIX, str(job.id)
            )
            source_path = job.source_file_path or os.path.join(job_dir, "source.mp4")
            
            job.status = "running"
            job.current_step = "transcribe"
            job.review_state = "none"
            job.stage_progress = 40
            job.progress = 40
            await db.commit()
            self._update_state(progress=40)
            
            try:
                await self._send_telegram(job, "🎙 Đang thử lại trích xuất nội dung (STT)...")
                understanding = await video_understanding_service.understand(
                    source_path, job_dir
                )
                transcript = understanding["transcript"]
                transcript_lang = understanding["language"]
                srt_content = understanding.get("srt_content", "")
            except (VideoUnderstandingError, Exception) as e:
                logger.warning("Transcription failed for job %s: %s", job_id, e)
                job.status = "failed"
                job.error_code = "transcription_failed"
                job.error_message = str(e)
                await db.commit()
                await self._send_telegram(
                    job,
                    f"❌ Thử lại Speech-to-Text thất bại: {e}",
                )
                return

            if not transcript or not transcript.strip():
                job.status = "failed"
                job.error_code = "transcription_failed"
                job.error_message = "Transcription produced empty text"
                await db.commit()
                await self._send_telegram(
                    job,
                    "❌ Thử lại Speech-to-Text thất bại: Phụ đề trống.",
                )
                return

            # Save raw.srt and raw.txt
            srt_path = os.path.join(job_dir, "raw.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            text_path = os.path.join(job_dir, "raw.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            job.transcript = transcript
            job.transcript_language = transcript_lang
            job.transcript_srt_path = srt_path
            job.transcript_text_path = text_path
            job.transcript_review_status = "pending"
            job.status = "waiting_review"
            job.current_step = "transcribe"
            job.review_state = "waiting_srt"
            job.stage_progress = 100
            job.progress = 50
            await db.commit()
            
            await self._send_telegram(
                job, "📝 Đã hoàn thành Speech-to-Text. Chờ duyệt phụ đề..."
            )
            await telegram_bot._send_srt_review(job.id)

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
                job.status = "running"
                job.current_step = "watermark"
                job.review_state = "none"
                job.stage_progress = 10
                job.progress = 90
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
                job.status = "running"
                job.current_step = "watermark"
                job.review_state = "none"
                job.stage_progress = 50
                job.progress = 92
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
                job.status = "running"
                job.current_step = "upload"
                job.review_state = "none"
                job.stage_progress = 50
                job.progress = 95
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
                job.current_step = "upload"
                job.review_state = "none"
                job.stage_progress = 100
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
