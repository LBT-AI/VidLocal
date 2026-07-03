import asyncio
import json
import logging
import os
import re
import html
from typing import Optional, Dict
from uuid import UUID

from app.config import settings
from app.database import get_async_session
from app.models.video_job import VideoJob
from app.models.character_glossary import CharacterGlossary
from app.models.character_glossary_draft import CharacterGlossaryDraft, CharacterGlossaryItem
from app.services.glossary_service import glossary_service
from app.services.character_extraction_service import character_extraction_service
from app.services.thumbnail_service import thumbnail_prompt_service
from app.services.facebook_download_service import facebook_download_service
from app.services.tiktok_download_service import tiktok_download_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

FACEBOOK_URL_PATTERN = re.compile(
    r"https?://(?:www\.|m\.|mbasic\.)?(?:facebook\.com|fb\.watch)/[\w./\-?&=]+"
)

TIKTOK_URL_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|m\.)?(?:tiktok\.com)/[\w./\-?&=]+"
)


class TelegramBotService:
    def __init__(self):
        self.application: Optional[object] = None
        self._token: str = ""
        self._admin_chat_id: str = ""
        self._waiting_edit: Dict[int, dict] = {}

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._admin_chat_id)

    def configure(self):
        self._token = settings.TELEGRAM_BOT_TOKEN
        self._admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

    def _check_admin(self, chat_id: int) -> bool:
        return str(chat_id) == self._admin_chat_id

    def _escape(self, text: str) -> str:
        return html.escape(text)

    def _progress_bar(self, percent: int, width: int = 12) -> str:
        filled = round(percent / 100 * width)
        empty = width - filled
        return f"▓" * filled + f"░" * empty

    def _section_divider(self) -> str:
        return "\n" + "─" * 30 + "\n"

    def _format_job_card(self, job) -> str:
        duration = ""
        if job.duration_seconds:
            m, s = divmod(int(job.duration_seconds), 60)
            h, m = divmod(m, 60)
            duration = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{m:02d}:{s:02d}"
        lines = [
            f"🎬 <b>Video Processed</b>",
            f"📹 <b>Name:</b> {self._escape(job.ai_title or 'Untitled')}",
        ]
        if duration:
            lines.append(f"⏱️ <b>Duration:</b> {duration}")
        if job.ai_category:
            lines.append(f"🏷️ <b>Category:</b> {self._escape(job.ai_category)}")
        lines.append(f"📊 <b>Progress:</b> {job.progress}%")
        return "\n".join(lines)

    def _status_line(self, label: str, status: str) -> str:
        icons = {
            "pending": "⏳", "processing": "🔄", "completed": "✅",
            "approved": "✅", "generated": "✅", "done": "✅",
            "failed": "❌", "error": "❌", "cancelled": "⛔",
            "skipped": "⏭️", "rejected": "⛔",
        }
        icon = icons.get(status.lower(), "⏳") if status else "⏳"
        return f"{icon} <b>{label}:</b> {status or 'pending'}"

    def _format_preview(self, job: VideoJob) -> str:
        title = job.ai_title or "Đang tạo..."
        description = job.ai_description or ""
        tags = []
        if job.ai_tags:
            try:
                tags = json.loads(job.ai_tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
        hashtags = []
        if job.ai_hashtags:
            try:
                hashtags = json.loads(job.ai_hashtags)
            except (json.JSONDecodeError, TypeError):
                hashtags = []
        risk_flags = []
        if job.risk_flags:
            try:
                risk_flags = json.loads(job.risk_flags)
            except (json.JSONDecodeError, TypeError):
                risk_flags = []
        summary = job.ai_summary or ""
        hook = job.ai_hook or ""

        meta_status = self._status_line("Metadata", job.metadata_status or "pending")
        gloss_status = self._status_line("Glossary", job.glossary_status or "pending")
        thumb_status = self._status_line("Thumbnail", job.thumbnail_status or "pending")

        lines = [
            f"🎬 <b>SEO Preview</b>  ·  <code>{str(job.id)[:8]}</code>",
            self._section_divider(),
            f"📌 <b>Title</b>",
            f"  {self._escape(title)}",
            "",
            f"📝 <b>Description</b>",
            f"  {self._escape(description[:200])}{'…' if len(description) > 200 else ''}" if description else "  (trống)",
            "",
            f"🏷 <b>Tags</b>",
            f"  {', '.join(self._escape(t) for t in tags[:10]) if tags else '(trống)'}",
            "",
            f"#️⃣ <b>Hashtags</b>",
            f"  {' '.join(self._escape(h) for h in hashtags) if hashtags else '(trống)'}",
            "",
            f"📂 <b>Category:</b> {self._escape(job.ai_category or '22 - People & Blogs')}",
            "",
            f"📋 <b>Summary</b>",
            f"  {self._escape(summary[:150])}{'…' if len(summary) > 150 else ''}" if summary else "  (trống)",
            "",
            f"🎣 <b>Hook</b>",
            f"  {self._escape(hook[:100])}{'…' if len(hook) > 100 else ''}" if hook else "  (trống)",
            self._section_divider(),
            meta_status,
            gloss_status,
            thumb_status,
        ]
        if risk_flags:
            lines.append(f"\n⚠️ <b>Risk:</b> {', '.join(self._escape(f) for f in risk_flags)}")
        else:
            lines.append("\n✅ <b>Risk:</b> Clean")
        return "\n".join(lines)

    async def _send_or_edit(self, chat_id: int, message_id: Optional[int], text: str, reply_markup=None):
        if not self.application:
            return None
        bot = self.application.bot
        try:
            if message_id:
                return await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                return msg
        except Exception as e:
            logger.warning("Telegram send/edit failed: %s", e)
            return None

    async def _start(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        if not self._check_admin(upd.effective_chat.id):
            await upd.message.reply_text("⛔ Bạn không phải admin.")
            return
        await upd.message.reply_text(
            "🤖 <b>VidLocal Bot</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Gửi link Facebook/TikTok để bắt đầu pipeline:\n"
            "📥 Tải video → 📝 Transcription → 🤖 AI SEO → 🎨 Thumbnail → 🚀 YouTube\n\n"
            "Dùng /help để xem hướng dẫn chi tiết.",
            parse_mode="HTML",
        )

    async def _help(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        if not self._check_admin(upd.effective_chat.id):
            return
        await upd.message.reply_text(
            "📖 <b>VidLocal Guide</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📤 <b>Gửi link</b> Facebook / TikTok → Bot tự động xử lý\n\n"
            "<b>Pipeline:</b>\n"
            "1️⃣ Tải video + transcript\n"
            "2️⃣ AI phân tích nhân vật (glossary)\n"
            "3️⃣ Tạo SEO metadata (title, desc, tags...)\n"
            "4️⃣ 🎨 Thumbnail AI (chọn frame → prompt → upload)\n"
            "5️⃣ 🚀 Upload YouTube\n\n"
            "<b>Lệnh:</b>\n"
            "🔹 /status &lt;job_id&gt;  —  Kiểm tra trạng thái\n"
            "🔹 /glossary  —  Quản lý từ điển nhân vật\n"
            "🔹 /add_glossary  —  Thêm entry\n"
            "🔹 /list_glossary  —  Danh sách\n"
            "🔹 /delete_glossary  —  Xóa\n"
            "🔹 /cancel_edit  —  Hủy thao tác\n\n"
            "📌 <b>Định dạng link:</b>\n"
            "• fb.com/.../videos/...\n"
            "• fb.watch/...\n"
            "• tiktok.com/@user/video/...\n"
            "• vm.tiktok.com/...",
            parse_mode="HTML",
        )

    async def _status(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        if not self._check_admin(upd.effective_chat.id):
            return
        if not ctx.args:
            await upd.message.reply_text("⚠️ Dùng: /status &lt;job_id&gt;", parse_mode="HTML")
            return
        try:
            job_uuid = UUID(ctx.args[0])
        except ValueError:
            await upd.message.reply_text("⚠️ Job ID không hợp lệ.")
            return
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
        if not job:
            await upd.message.reply_text("❌ Job không tồn tại.")
            return
        bar = self._progress_bar(job.progress)
        text = (
            f"📋 <b>Job Status</b>  ·  <code>{str(job.id)[:8]}</code>"
            f"{self._section_divider()}"
            f"📌 <b>Status:</b> {job.status}"
            f"\n📊 <b>{job.progress}%</b>"
            f"\n{bar}"
            f"{self._section_divider()}"
            f"{self._status_line('Metadata', job.metadata_status or 'pending')}"
            f"\n{self._status_line('Glossary', job.glossary_status or 'pending')}"
            f"\n{self._status_line('Thumbnail', job.thumbnail_status or 'pending')}"
            f"{self._section_divider()}"
            f"🔗 {self._escape(job.source_url[:80]) if job.source_url else 'N/A'}"
        )
        if job.youtube_url:
            text += f"\n📺 <a href='{job.youtube_url}'>Xem trên YouTube</a>"
        if job.error_message:
            text += f"\n❌ {self._escape(job.error_message[:200])}"
        await upd.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)

    async def _handle_message(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        if not self._check_admin(upd.effective_chat.id):
            return
        chat_id = upd.effective_chat.id
        text = (upd.message.text or "").strip()
        if not text:
            return

        chat_id_int = chat_id
        if chat_id_int in self._waiting_edit:
            await self._handle_edit_input(chat_id_int, text, upd)
            return

        is_fb = bool(FACEBOOK_URL_PATTERN.match(text))
        is_tt = bool(TIKTOK_URL_PATTERN.match(text))

        if not is_fb and not is_tt:
            await upd.message.reply_text(
                "⚠️ Đây không phải link Facebook hoặc TikTok hợp lệ.\n"
                "Gửi link video/reel từ Facebook hoặc TikTok.\n"
                "Dùng /help để xem hướng dẫn."
            )
            return

        if is_fb:
            if not facebook_download_service.validate_url(text):
                await upd.message.reply_text(
                    "⚠️ Link Facebook không đúng định dạng video.\n"
                    "Hãy gửi link dạng:\n"
                    "- https://facebook.com/.../videos/...\n"
                    "- https://facebook.com/reel/..."
                )
                return
            job_type = "facebook_to_youtube"
            source_platform = "facebook"
            worker_task = "workers.facebook_to_youtube_worker.process"
        else:
            if not tiktok_download_service.validate_url(text):
                await upd.message.reply_text(
                    "⚠️ Link TikTok không đúng định dạng video.\n"
                    "Hãy gửi link dạng:\n"
                    "- https://tiktok.com/@user/video/...\n"
                    "- https://vm.tiktok.com/..."
                )
                return
            job_type = "tiktok_to_youtube"
            source_platform = "tiktok"
            worker_task = "workers.tiktok_to_youtube_worker.process"

        msg = await upd.message.reply_text("⏳ Đang tạo job và xử lý...")
        job = VideoJob(
            type=job_type,
            source_url=text,
            source_platform=source_platform,
            target_platform="youtube",
            status="pending",
            metadata_status="pending",
            admin_chat_id=str(chat_id),
            telegram_message_id=msg.message_id,
        )
        async_session_inst = get_async_session()
        async with async_session_inst() as db:
            db.add(job)
            await db.commit()
            job_id_str = str(job.id)
        await msg.edit_text(
            f"✅ Job đã tạo!\n"
            f"🆔 Job ID: <code>{job_id_str}</code>\n"
            f"📥 Đang tải video, trích xuất nội dung...",
            parse_mode="HTML",
        )
        celery_app.send_task(worker_task, args=[job_id_str])

    async def _handle_edit_input(self, chat_id: int, text: str, upd):
        from telegram import Update
        state = self._waiting_edit.pop(chat_id, None)
        if not state:
            return
        job_id = state["job_id"]
        field = state["field"]
        if field.startswith("gloss_"):
            await self._handle_glossary_edit_input(chat_id, text, upd, state)
            return
        if field == "thumbnail_upload":
            await upd.message.reply_text("⚠️ Vui lòng gửi ảnh (JPEG/PNG), không phải text.")
            self._waiting_edit[chat_id] = state
            return
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                await upd.message.reply_text("❌ Job không tồn tại.")
                return
            if field == "title":
                job.ai_title = text[:90]
            elif field == "description":
                job.ai_description = text
            job.metadata_status = "generated"
            await db.commit()
        await upd.message.reply_text(
            f"✅ Đã cập nhật {field}!\n"
            f"Giá trị mới:\n{text[:500]}"
        )
        await self._send_preview(chat_id, job_id)

    async def _handle_glossary_edit_input(self, chat_id: int, text: str, upd, state):
        job_id = state["job_id"]
        draft_id = state.get("draft_id")
        field = state["field"]
        if field == "gloss_add":
            parts = text.split("|")
            if len(parts) < 2:
                await upd.message.reply_text(
                    "⚠️ Cần ít nhất source_name và target_name, cách nhau bằng dấu |\n"
                    "Ví dụ: <code>Lão Vương|Ông Vương||hàng xóm|male||láng giềng</code>",
                    parse_mode="HTML",
                )
                self._waiting_edit[chat_id] = state
                return
            source = parts[0].strip()
            target = parts[1].strip()
            aliases = [a.strip() for a in parts[2].split(",")] if len(parts) > 2 and parts[2].strip() else None
            role = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
            gender = parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
            pronoun_style = parts[5].strip() if len(parts) > 5 and parts[5].strip() else None
            notes = parts[6].strip() if len(parts) > 6 and parts[6].strip() else None
            async_session = get_async_session()
            async with async_session() as db:
                from sqlalchemy import select
                item = CharacterGlossaryItem(
                    job_id=job_id,
                    draft_id=draft_id,
                    category="character",
                    source_name=source,
                    target_name=target,
                    aliases=aliases or [],
                    role=role,
                    gender=gender,
                    pronoun_style=pronoun_style,
                    notes=notes,
                    approved=True,
                )
                db.add(item)
                await db.commit()
            await upd.message.reply_text(f"✅ Đã thêm: {source} → {target}")
            await self._send_glossary_review(job_id)
        elif field.startswith("gloss_edit:"):
            parts = field.split(":")
            item_idx = int(parts[1])
            edit_field = parts[2]
            async_session = get_async_session()
            async with async_session() as db:
                from sqlalchemy import select
                items_result = await db.execute(
                    select(CharacterGlossaryItem)
                    .where(CharacterGlossaryItem.draft_id == draft_id)
                    .order_by(CharacterGlossaryItem.category, CharacterGlossaryItem.source_name)
                )
                items = list(items_result.scalars().all())
                if item_idx >= len(items):
                    await upd.message.reply_text("❌ Không tìm thấy mục.")
                    return
                item = items[item_idx]
                if edit_field == "source_name":
                    item.source_name = text.strip()
                elif edit_field == "target_name":
                    item.target_name = text.strip()
                elif edit_field == "role":
                    item.role = text.strip()
                elif edit_field == "aliases":
                    item.aliases = [a.strip() for a in text.split(",")]
                else:
                    await upd.message.reply_text(f"❌ Không hỗ trợ sửa trường {edit_field}")
                    return
                await db.commit()
            await upd.message.reply_text(f"✅ Đã cập nhật {edit_field}!")
            await self._send_glossary_review(job_id)

    async def _send_preview(self, chat_id: int, job_id: str):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            text = self._format_preview(job)
            reply_markup = self._build_main_actions(job_id)
            msg = await self._send_or_edit(chat_id, job.telegram_message_id, text, reply_markup)
            if msg and job.telegram_message_id is None:
                job.telegram_message_id = msg.message_id
                await db.commit()

    def _build_main_actions(self, job_id: str):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("✨ SEO Metadata", callback_data=f"seo_menu|{job_id}"),
                InlineKeyboardButton("🎨 Thumbnail AI", callback_data=f"thumbnail_gen|{job_id}"),
            ],
            [
                InlineKeyboardButton("👁 Preview Video", callback_data=f"preview_video|{job_id}"),
                InlineKeyboardButton("📂 Files", callback_data=f"files_menu|{job_id}"),
            ],
            [
                InlineKeyboardButton("🚀 Upload YouTube", callback_data=f"upload_menu|{job_id}"),
                InlineKeyboardButton("🗑 Hủy", callback_data=f"cancel|{job_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _build_seo_menu(self, job_id: str):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("🚀 Upload YouTube", callback_data=f"approve|{job_id}"),
                InlineKeyboardButton("🔄 Regenerate", callback_data=f"regenerate|{job_id}"),
            ],
            [
                InlineKeyboardButton("✏️ Sửa tiêu đề", callback_data=f"edit_title|{job_id}"),
                InlineKeyboardButton("📝 Sửa mô tả", callback_data=f"edit_desc|{job_id}"),
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data=f"main_menu|{job_id}"),
                InlineKeyboardButton("🗑 Hủy job", callback_data=f"cancel|{job_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _build_upload_menu(self, job_id: str):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("🚀 Upload YouTube", callback_data=f"approve|{job_id}"),
            ],
            [
                InlineKeyboardButton("✏️ Sửa tiêu đề", callback_data=f"edit_title|{job_id}"),
                InlineKeyboardButton("📝 Sửa mô tả", callback_data=f"edit_desc|{job_id}"),
            ],
            [
                InlineKeyboardButton("🎨 Sửa thumbnail", callback_data=f"thumbnail_gen|{job_id}"),
                InlineKeyboardButton("🔄 Tạo lại SEO", callback_data=f"regenerate|{job_id}"),
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data=f"main_menu|{job_id}"),
                InlineKeyboardButton("🗑 Hủy job", callback_data=f"cancel|{job_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _handle_callback(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        query = upd.callback_query
        await query.answer()
        if not self._check_admin(query.from_user.id):
            await query.edit_message_text("⛔ Bạn không phải admin.")
            return
        data = query.data or ""
        if data.startswith("gloss_"):
            await self._handle_glossary_callback(update, context)
            return
        parts = data.split("|", 1)
        if len(parts) != 2:
            return
        action, job_id = parts
        chat_id = query.message.chat_id
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            await query.edit_message_text("❌ Job ID không hợp lệ.")
            return

        if action == "main_menu":
            await self._send_preview(chat_id, str(job_uuid))
        elif action == "seo_menu":
            async with get_async_session()() as db:
                from sqlalchemy import select
                result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
                job = result.scalar_one_or_none()
                if job:
                    text = self._format_preview(job)
                    reply_markup = self._build_seo_menu(str(job_uuid))
                    await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)
        elif action == "upload_menu":
            async with get_async_session()() as db:
                from sqlalchemy import select
                result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
                job = result.scalar_one_or_none()
                if job:
                    text = self._format_preview(job)
                    reply_markup = self._build_upload_menu(str(job_uuid))
                    await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)
        elif action == "preview_video":
            await self._callback_preview_video(chat_id, query, job_uuid)
        elif action == "files_menu":
            await self._callback_files_menu(chat_id, query, job_uuid)
        elif action == "approve":
            await self._callback_approve(chat_id, query, job_uuid)
        elif action == "regenerate":
            await self._callback_regenerate(chat_id, query, job_uuid)
        elif action == "edit_title":
            self._waiting_edit[chat_id] = {"job_id": job_uuid, "field": "title"}
            await query.edit_message_text(
                "✏️ Gửi title mới (tối đa 90 ký tự):\n"
                "Gõ /cancel_edit để hủy."
            )
        elif action == "edit_desc":
            self._waiting_edit[chat_id] = {"job_id": job_uuid, "field": "description"}
            await query.edit_message_text(
                "✏️ Gửi description mới:\n"
                "Gõ /cancel_edit để hủy."
            )
        elif action == "cancel":
            await self._callback_cancel(chat_id, query, job_uuid)
        elif action.startswith("thumbnail_"):
            await self._handle_thumbnail_callback(chat_id, query, data, job_uuid)

    async def _glossary_help(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        if not self._check_admin(upd.effective_chat.id):
            return
        await upd.message.reply_text(
            "📖 <b>Glossary Guide</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Glossary đảm bảo AI dịch đúng tên nhân vật.\n\n"
            "<b>Commands:</b>\n"
            "/add_glossary — Thêm entry mới\n"
            "/list_glossary — Xem danh sách\n"
            "/delete_glossary — Xóa entry\n\n"
            "<b>Format:</b>\n"
            "<code>/add_glossary 小明|Tiểu Minh||nam|thân mật|anh hùng chính</code>\n"
            "source|target|aliases|gender|pronoun|notes",
            parse_mode="HTML",
        )

    async def _add_glossary(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        if not self._check_admin(upd.effective_chat.id):
            return
        if not ctx.args:
            await upd.message.reply_text(
                "⚠️ Dùng: /add_glossary &lt;source&gt;|&lt;target&gt; [|aliases|gender|pronoun_style|note]\n"
                "Ví dụ: /add_glossary 小明|Tiểu Minh||nam|thân mật|nhân vật chính",
                parse_mode="HTML",
            )
            return
        parts = " ".join(ctx.args).split("|")
        if len(parts) < 2:
            await upd.message.reply_text("⚠️ Cần ít nhất source_name và target_name, cách nhau bằng dấu |")
            return
        source = parts[0].strip()
        target = parts[1].strip()
        aliases = [a.strip() for a in parts[2].split(",")] if len(parts) > 2 and parts[2].strip() else None
        gender = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
        pronoun_style = parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
        note = parts[5].strip() if len(parts) > 5 and parts[5].strip() else None
        try:
            entry = await glossary_service.add_entry(
                source_name=source,
                target_name=target,
                aliases=aliases,
                gender=gender,
                pronoun_style=pronoun_style,
                note=note,
            )
            await upd.message.reply_text(
                f"✅ Added glossary:\n"
                f"<b>{self._escape(source)}</b> → <b>{self._escape(target)}</b>\n"
                f"🆔 {entry.id}",
                parse_mode="HTML",
            )
        except Exception as e:
            await upd.message.reply_text(f"❌ Lỗi: {e}")

    async def _list_glossary(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        if not self._check_admin(upd.effective_chat.id):
            return
        try:
            entries = await glossary_service.list_entries()
        except Exception as e:
            await upd.message.reply_text(f"❌ Lỗi: {e}")
            return
        if not entries:
            await upd.message.reply_text("📭 Chưa có glossary entries nào.")
            return
        lines = ["📋 <b>Glossary Entries:</b>\n"]
        for e in entries:
            aliases_str = f" [aliases: {', '.join(e.aliases)}]" if e.aliases else ""
            gender_str = f" ({e.gender})" if e.gender else ""
            pronoun_str = f" - xưng hô: {e.pronoun_style}" if e.pronoun_style else ""
            note_str = f" - {e.note}" if e.note else ""
            lines.append(
                f"🆔 <code>{e.id}</code>\n"
                f"{self._escape(e.source_name)} → {self._escape(e.target_name)}{aliases_str}{gender_str}{pronoun_str}{note_str}\n"
            )
        await upd.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _delete_glossary(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        if not self._check_admin(upd.effective_chat.id):
            return
        if not ctx.args:
            await upd.message.reply_text("⚠️ Dùng: /delete_glossary &lt;entry_id&gt;")
            return
        try:
            entry_id = UUID(ctx.args[0])
        except ValueError:
            await upd.message.reply_text("⚠️ ID không hợp lệ.")
            return
        success = await glossary_service.delete_entry(entry_id)
        if success:
            await upd.message.reply_text(f"✅ Đã xóa glossary entry <code>{entry_id}</code>", parse_mode="HTML")
        else:
            await upd.message.reply_text(f"❌ Không tìm thấy entry <code>{entry_id}</code>", parse_mode="HTML")

    async def _send_glossary_review(self, job_id: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job or not job.admin_chat_id:
                return
            chat_id = int(job.admin_chat_id)
            if not job.glossary_draft_id:
                return
            draft_result = await db.execute(
                select(CharacterGlossaryDraft).where(CharacterGlossaryDraft.id == job.glossary_draft_id)
            )
            draft = draft_result.scalar_one_or_none()
            if not draft:
                return
            items_result = await db.execute(
                select(CharacterGlossaryItem)
                .where(CharacterGlossaryItem.draft_id == draft.id)
                .order_by(CharacterGlossaryItem.category, CharacterGlossaryItem.source_name)
            )
            items = list(items_result.scalars().all())
            text = character_extraction_service.format_draft_for_review(draft, items)
            reply_markup = self._build_glossary_keyboard(str(job.id), draft.id, items)
            await self._send_or_edit(chat_id, None, text, reply_markup)

    def _build_glossary_keyboard(self, job_id: str, draft_id: UUID, items: list = None):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        if items:
            for i, item in enumerate(items):
                emoji = "🏢" if item.category == "organization" else "📍" if item.category == "place" else "👤"
                label = f"{emoji} {item.source_name} → {item.target_name}"
                keyboard.append([
                    InlineKeyboardButton(label[:40], callback_data=f"gloss_edit_list|{job_id}|{draft_id}|{i}")
                ])
        keyboard.append([
            InlineKeyboardButton("✅ Duyệt tất cả", callback_data=f"gloss_approve|{job_id}|{draft_id}"),
        ])
        keyboard.append([
            InlineKeyboardButton("➕ Thêm", callback_data=f"gloss_add|{job_id}|{draft_id}"),
            InlineKeyboardButton("🔁 Quét lại", callback_data=f"gloss_rescan|{job_id}|{draft_id}"),
            InlineKeyboardButton("⏭ Bỏ qua", callback_data=f"gloss_skip|{job_id}|{draft_id}"),
        ])
        return InlineKeyboardMarkup(keyboard)

    def _build_glossary_edit_keyboard(self, job_id: str, draft_id: UUID, item_idx: int, total: int):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        nav_row = []
        if item_idx > 0:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"gloss_edit_nav|{job_id}|{draft_id}|{item_idx - 1}"))
        nav_row.append(InlineKeyboardButton(f"{item_idx + 1}/{total}", callback_data=f"gloss_noop|{job_id}"))
        if item_idx < total - 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"gloss_edit_nav|{job_id}|{draft_id}|{item_idx + 1}"))
        buttons.append(nav_row)
        buttons.append([
            InlineKeyboardButton("✏️ Sửa tên", callback_data=f"gloss_edit_field|{job_id}|{draft_id}|{item_idx}|source_name"),
            InlineKeyboardButton("📝 Sửa target", callback_data=f"gloss_edit_field|{job_id}|{draft_id}|{item_idx}|target_name"),
        ])
        buttons.append([
            InlineKeyboardButton("🏷 Vai trò", callback_data=f"gloss_edit_field|{job_id}|{draft_id}|{item_idx}|role"),
            InlineKeyboardButton("📎 Aliases", callback_data=f"gloss_edit_field|{job_id}|{draft_id}|{item_idx}|aliases"),
        ])
        buttons.append([
            InlineKeyboardButton("🗑 Xóa", callback_data=f"gloss_delete_item|{job_id}|{draft_id}|{item_idx}"),
            InlineKeyboardButton("⬅️ Quay lại", callback_data=f"gloss_back|{job_id}|{draft_id}"),
        ])
        return InlineKeyboardMarkup(buttons)

    async def _handle_glossary_callback(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        query = upd.callback_query
        await query.answer()
        if not self._check_admin(query.from_user.id):
            await query.edit_message_text("⛔ Bạn không phải admin.")
            return
        data = query.data or ""
        parts = data.split("|")
        action = parts[0]
        job_id = parts[1]
        draft_id = UUID(parts[2]) if len(parts) > 2 else None
        chat_id = query.message.chat_id
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            await query.edit_message_text("❌ Job ID không hợp lệ.")
            return

        if action == "gloss_approve":
            await self._callback_gloss_approve(chat_id, query, job_uuid, draft_id)
        elif action == "gloss_skip":
            await self._callback_gloss_skip(chat_id, query, job_uuid)
        elif action == "gloss_rescan":
            await self._callback_gloss_rescan(chat_id, query, job_uuid)
        elif action == "gloss_add":
            self._waiting_edit[chat_id] = {"job_id": job_uuid, "draft_id": draft_id, "field": "gloss_add"}
            await query.edit_message_text(
                "➕ Gửi thông tin nhân vật mới theo định dạng:\n"
                "<code>source_name|target_name|aliases|role|gender|pronoun_style|notes</code>\n\n"
                "Ví dụ: <code>Lão Vương|Ông Vương||hàng xóm|male|bác|láng giềng thân thiết</code>\n\n"
                "Gõ /cancel_edit để hủy.",
                parse_mode="HTML",
            )
        elif action == "gloss_edit_list":
            await self._show_glossary_edit_item(chat_id, query, job_uuid, draft_id, 0)
        elif action == "gloss_edit_nav":
            item_idx = int(parts[3])
            await self._show_glossary_edit_item(chat_id, query, job_uuid, draft_id, item_idx)
        elif action == "gloss_edit_field":
            item_idx = int(parts[3])
            field = parts[4]
            self._waiting_edit[chat_id] = {
                "job_id": job_uuid, "draft_id": draft_id,
                "field": f"gloss_edit:{item_idx}:{field}"
            }
            field_labels = {
                "source_name": "tên gốc (source_name)",
                "target_name": "tên dịch (target_name)",
                "role": "vai trò",
                "aliases": "tên gọi khác (cách nhau bằng dấu phẩy)",
            }
            label = field_labels.get(field, field)
            await query.edit_message_text(
                f"✏️ Gửi {label} mới:\n"
                "Gõ /cancel_edit để hủy.",
                parse_mode="HTML",
            )
        elif action == "gloss_delete_item":
            item_idx = int(parts[3])
            await self._callback_gloss_delete_item(chat_id, query, job_uuid, draft_id, item_idx)
        elif action == "gloss_noop":
            await query.answer()
        elif action == "gloss_back":
            await self._send_glossary_review(job_uuid)

    async def _show_glossary_edit_item(self, chat_id: int, query, job_uuid: UUID, draft_id: UUID, item_idx: int):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            items_result = await db.execute(
                select(CharacterGlossaryItem)
                .where(CharacterGlossaryItem.draft_id == draft_id)
                .order_by(CharacterGlossaryItem.category, CharacterGlossaryItem.source_name)
            )
            items = list(items_result.scalars().all())
            if item_idx >= len(items):
                await query.edit_message_text("❌ Không tìm thấy mục này.")
                return
            item = items[item_idx]
            emoji = "🏢" if item.category == "organization" else "📍" if item.category == "place" else "👤"
            gender_label = {"male": "Nam", "female": "Nữ", "unknown": "Không rõ"}.get(item.gender or "", item.gender or "")
            text = (
                f"{emoji} <b>{self._escape(item.source_name)}</b>"
                f"{self._section_divider()}"
                f"<b>Tên gốc:</b> {self._escape(item.source_name)}\n"
                f"<b>Tên dịch:</b> {self._escape(item.target_name)}\n"
            )
            if item.role:
                text += f"<b>Vai trò:</b> {self._escape(item.role)}\n"
            if item.aliases:
                text += f"<b>Bí danh:</b> {', '.join(str(a) for a in item.aliases)}\n"
            if item.family_clan:
                text += f"<b>Gia tộc:</b> {self._escape(item.family_clan)}\n"
            if gender_label:
                text += f"<b>Giới tính:</b> {gender_label}\n"
            if item.pronoun_style:
                text += f"<b>Xưng hô:</b> {self._escape(item.pronoun_style)}\n"
            if item.notes:
                text += f"<b>Ghi chú:</b> {self._escape(item.notes)}\n"
            reply_markup = self._build_glossary_edit_keyboard(str(job_uuid), draft_id, item_idx, len(items))
            await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_gloss_approve(self, chat_id: int, query, job_uuid: UUID, draft_id: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            job.glossary_status = "approved"
            if draft_id:
                draft_result = await db.execute(
                    select(CharacterGlossaryDraft).where(CharacterGlossaryDraft.id == draft_id)
                )
                draft = draft_result.scalar_one_or_none()
                if draft:
                    draft.status = "approved"
            await db.commit()
        await query.edit_message_text("✅ Đã duyệt glossary! Đang tiếp tục xử lý...")
        from app.workers.celery_app import celery_app
        celery_app.send_task(
            "workers.facebook_to_youtube_worker.process_after_glossary",
            args=[str(job_uuid)],
        )

    async def _callback_gloss_skip(self, chat_id: int, query, job_uuid: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            job.glossary_status = "skipped"
            await db.commit()
        await query.edit_message_text(
            "⏭ Đã bỏ qua glossary. ⚠️ Tên nhân vật có thể không nhất quán khi dịch.\n"
            "Đang tiếp tục xử lý..."
        )
        from app.workers.celery_app import celery_app
        celery_app.send_task(
            "workers.facebook_to_youtube_worker.process_after_glossary",
            args=[str(job_uuid)],
        )

    async def _callback_gloss_rescan(self, chat_id: int, query, job_uuid: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            transcript = job.transcript or ""
        await query.edit_message_text("🔄 Đang quét lại nhân vật...")
        extraction_data = character_extraction_service.extract(transcript)
        draft, items = await character_extraction_service.save_draft(job_uuid, extraction_data)
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if job:
                job.glossary_draft_id = draft.id
                job.glossary_status = "pending"
                await db.commit()
        text = character_extraction_service.format_draft_for_review(draft, items)
        reply_markup = self._build_glossary_keyboard(str(job_uuid), draft.id)
        await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_gloss_delete_item(self, chat_id: int, query, job_uuid: UUID, draft_id: UUID, item_idx: int):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            items_result = await db.execute(
                select(CharacterGlossaryItem)
                .where(CharacterGlossaryItem.draft_id == draft_id)
                .order_by(CharacterGlossaryItem.category, CharacterGlossaryItem.source_name)
            )
            items = list(items_result.scalars().all())
            if item_idx >= len(items):
                await query.edit_message_text("❌ Không tìm thấy mục này.")
                return
            item = items[item_idx]
            await db.delete(item)
            await db.commit()
        await self._send_glossary_review(job_uuid)

    async def _cancel_edit(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        chat_id = upd.effective_chat.id
        state = self._waiting_edit.pop(chat_id, None)
        if state:
            await upd.message.reply_text("✅ Đã hủy chỉnh sửa.")
            await self._send_preview(chat_id, state["job_id"])
        else:
            await upd.message.reply_text("⚠️ Không có chỉnh sửa nào đang chờ.")

    async def _callback_approve(self, chat_id: int, query, job_uuid: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            job.metadata_status = "approved"
            job.status = "approved"
            await db.commit()
            upload_task = (
                "workers.facebook_to_youtube_worker.upload_approved"
                if job.type == "facebook_to_youtube"
                else "workers.tiktok_to_youtube_worker.upload_approved"
            )
        await query.edit_message_text("📤 Đã duyệt! Đang chuẩn bị upload lên YouTube...")
        celery_app.send_task(upload_task, args=[str(job_uuid)])

    async def _callback_regenerate(self, chat_id: int, query, job_uuid: UUID):
        await query.edit_message_text("🔄 Đang tạo lại metadata...")
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            transcript = job.transcript or ""
            source_metadata = {}
            try:
                from app.services.seo_metadata_service import seo_metadata_service
                previous = None
                if job.ai_title:
                    previous = {
                        "title": job.ai_title,
                        "description": job.ai_description or "",
                        "tags": json.loads(job.ai_tags) if job.ai_tags else [],
                        "hashtags": json.loads(job.ai_hashtags) if job.ai_hashtags else [],
                        "category": job.ai_category or "",
                        "summary": job.ai_summary or "",
                        "hook": job.ai_hook or "",
                        "language": job.transcript_language or "vi",
                        "risk_flags": json.loads(job.risk_flags) if job.risk_flags else [],
                    }
                    meta = seo_metadata_service.regenerate(transcript, source_metadata, previous)
                else:
                    meta = seo_metadata_service.generate(transcript, source_metadata)
                job.ai_title = meta["title"][:90]
                job.ai_description = meta["description"]
                job.ai_tags = json.dumps(meta["tags"], ensure_ascii=False)
                job.ai_hashtags = json.dumps(meta["hashtags"], ensure_ascii=False)
                job.ai_summary = meta["summary"]
                job.ai_hook = meta["hook"]
                job.ai_category = meta["category"]
                job.risk_flags = json.dumps(meta["risk_flags"], ensure_ascii=False)
                job.metadata_status = "generated"
                await db.commit()
            except Exception as e:
                logger.error("Regenerate failed for job %s: %s", job_uuid, e)
                await query.edit_message_text(f"❌ Lỗi khi tạo lại metadata: {e}")
                return
        await self._send_preview(chat_id, str(job_uuid))

    async def _callback_cancel(self, chat_id: int, query, job_uuid: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if job:
                job.status = "cancelled"
                job.metadata_status = "rejected"
                await db.commit()
        await query.edit_message_text("❌ Job đã hủy.")

    async def _callback_preview_video(self, chat_id: int, query, job_uuid: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            source_path = job.source_file_path
            normalized_path = getattr(job, 'normalized_file_path', None) or ""
            previews = []
            if source_path and os.path.exists(source_path):
                previews.append(f"🎬 Source: <code>{source_path}</code>")
            if normalized_path and os.path.exists(normalized_path):
                previews.append(f"🎞 Normalized: <code>{normalized_path}</code>")
        lines = [
            f"👁 <b>Video Files</b>  ·  <code>{str(job_uuid)[:8]}</code>",
            self._section_divider(),
            *([f"📁 No video files found"] if not previews else previews),
            "",
            f"📹 <b>Title:</b> {self._escape(job.ai_title or 'Untitled')}",
            f"🔗 <b>Source:</b> {self._escape(job.source_url[:80]) if job.source_url else 'N/A'}",
        ]
        if job.youtube_url:
            lines.append(f"📺 <b>YouTube:</b> <a href='{job.youtube_url}'>Link</a>")
        text = "\n".join(lines)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data=f"main_menu|{job_uuid}")],
        ])
        await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_files_menu(self, chat_id: int, query, job_uuid: UUID):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            job_dir = job.temp_dir or ""
            files_list = []
            if job_dir and os.path.exists(job_dir):
                for fname in sorted(os.listdir(job_dir)):
                    fpath = os.path.join(job_dir, fname)
                    fsize = os.path.getsize(fpath)
                    size_str = f"{fsize / 1024 / 1024:.1f}MB" if fsize > 1024 * 1024 else f"{fsize / 1024:.1f}KB"
                    files_list.append(f"📄 <code>{fname}</code> ({size_str})")
            lines = [
                f"📂 <b>Project Files</b>  ·  <code>{str(job_uuid)[:8]}</code>",
                self._section_divider(),
                *([f"📭 No files found"] if not files_list else files_list),
            ]
        text = "\n".join(lines)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data=f"main_menu|{job_uuid}")],
        ])
        await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    def _format_reference_selection(self, ref_frames: list, job_id: str, selected_idx: int = None) -> str:
        nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        lines = [
            f"🖼 <b>Select Reference Frame</b>  ·  <code>{job_id[:8]}</code>",
            self._section_divider(),
        ]
        for i, ref in enumerate(ref_frames[:6]):
            s = ref.get("score", {})
            pot = s.get("thumbnail_potential", 0)
            has_face = ref.get("has_face", False)
            face_label = "👤 Face" if has_face else "🌄 Scene"
            marker = "✅" if selected_idx is not None and i == selected_idx else nums[i]
            desc = ref.get("face_description") or ref.get("scene_description") or ""
            lines.append(f"{marker} <b>Frame #{i + 1}</b>  ·  {face_label}  ·  {pot:.1f}pts")
            if desc:
                lines.append(f"   {self._escape(desc[:80])}")
        lines.append(self._section_divider())
        lines.append("👇 Chọn frame làm tham chiếu → AI tạo prompt thumbnail.")
        return "\n".join(lines)

    def _build_reference_keyboard(self, job_id: str, ref_frames: list, selected_idx: int = None):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        frame_row = []
        nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        for i in range(min(len(ref_frames), 6)):
            label = f"✅ {nums[i]}" if selected_idx is not None and i == selected_idx else nums[i]
            frame_row.append(InlineKeyboardButton(label, callback_data=f"thumbnail_ref_select|{job_id}|{i}"))
        if frame_row:
            buttons.append(frame_row)
        action_row = []
        if selected_idx is not None:
            action_row.append(InlineKeyboardButton("🎨 Tạo Prompt", callback_data=f"thumbnail_gen_prompts|{job_id}"))
        action_row.append(InlineKeyboardButton("🔁 Quét lại", callback_data=f"thumbnail_ref_rescan|{job_id}"))
        buttons.append(action_row if action_row else [InlineKeyboardButton("🔁 Quét lại", callback_data=f"thumbnail_ref_rescan|{job_id}")])
        buttons.append([
            InlineKeyboardButton("⏭ Skip", callback_data=f"thumbnail_skip|{job_id}"),
            InlineKeyboardButton("🔙 Back", callback_data=f"thumbnail_back|{job_id}"),
        ])
        return InlineKeyboardMarkup(buttons)

    def _format_thumbnail_prompts(self, prompts: list, job_id: str, ref_info: str = "") -> str:
        nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        style_emoji = {
            "Drama": "🎭", "Review phim": "🎬", "Xianxia/Anime": "🏔",
            "Viral CTR": "📈", "Cinematic": "🎥", "Anime": "🏔",
            "Poster": "🎬", "Character": "👤", "Close-up": "👤",
        }
        lines = [
            f"🎨 <b>Thumbnail AI</b>  ·  <code>{job_id[:8]}</code>",
            self._section_divider(),
        ]
        if ref_info:
            lines.append(f"📌 <b>Reference:</b> {self._escape(ref_info)}\n")
        for i, p in enumerate(prompts[:4]):
            style = p.get("style", "Unknown")
            emoji = style_emoji.get(style, "🎨")
            lines.append(f"{nums[i]} {emoji} <b>{self._escape(style)}</b>")
            prompt_text = p.get("prompt", "")
            if len(prompt_text) > 80:
                prompt_text = prompt_text[:77] + "..."
            lines.append(f"   <code>{self._escape(prompt_text)}</code>")
        lines.append(self._section_divider())
        lines.append("📋 <i>Chọn prompt → sao chép, dùng Midjourney/DALL-E tạo ảnh 1280x720.</i>")
        return "\n".join(lines)

    def _build_thumbnail_keyboard(self, job_id: str, prompts: list):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        buttons = []
        prompt_row = []
        for i in range(min(len(prompts), 4)):
            prompt_row.append(InlineKeyboardButton(nums[i], callback_data=f"thumbnail_copy|{job_id}|{i}"))
        if prompt_row:
            buttons.append(prompt_row)
        buttons.append([
            InlineKeyboardButton("📋 Sao chép Prompt", callback_data=f"thumbnail_copy_all|{job_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("🖼 Upload ảnh", callback_data=f"thumbnail_upload|{job_id}"),
            InlineKeyboardButton("👁 Xem ảnh", callback_data=f"thumbnail_preview|{job_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("🖼 Chọn frame", callback_data=f"thumbnail_refs|{job_id}"),
            InlineKeyboardButton("🔄 Tạo lại", callback_data=f"thumbnail_regen|{job_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("⏭ Skip", callback_data=f"thumbnail_skip|{job_id}"),
            InlineKeyboardButton("🔙 Back", callback_data=f"thumbnail_back|{job_id}"),
        ])
        return InlineKeyboardMarkup(buttons)

    async def _handle_thumbnail_callback(self, chat_id: int, query, data: str, job_uuid):
        parts = data.split("|")
        action = parts[0]
        job_id_str = str(job_uuid)

        if action == "thumbnail_gen":
            await self._callback_thumbnail_gen_extract(chat_id, query, job_uuid)
        elif action == "thumbnail_refs":
            await self._callback_thumbnail_show_refs(chat_id, query, job_uuid)
        elif action == "thumbnail_ref_select":
            idx = int(parts[2])
            await self._callback_thumbnail_ref_select(chat_id, query, job_uuid, idx)
        elif action == "thumbnail_ref_rescan":
            await self._callback_thumbnail_gen_extract(chat_id, query, job_uuid, rescan=True)
        elif action == "thumbnail_gen_prompts":
            await self._callback_thumbnail_generate(chat_id, query, job_uuid)
        elif action == "thumbnail_copy":
            idx = int(parts[2])
            await self._callback_thumbnail_copy(chat_id, query, job_uuid, idx)
        elif action == "thumbnail_upload":
            self._waiting_edit[chat_id] = {"job_id": job_uuid, "field": "thumbnail_upload"}
            await query.edit_message_text(
                "⬆️ Gửi ảnh thumbnail (JPEG/PNG, 1280x720) mà bạn đã tạo từ Google Flow.\n"
                "Gõ /cancel_edit để hủy.",
                parse_mode="HTML",
            )
        elif action == "thumbnail_preview":
            await self._callback_thumbnail_preview(chat_id, query, job_uuid)
        elif action == "thumbnail_regen":
            await self._callback_thumbnail_generate(chat_id, query, job_uuid, regenerate=True)
        elif action == "thumbnail_copy_all":
            await self._callback_thumbnail_copy_all(chat_id, query, job_uuid)
        elif action == "thumbnail_skip":
            await self._callback_thumbnail_skip(chat_id, query, job_uuid)
        elif action == "thumbnail_back":
            await self._send_preview(chat_id, str(job_uuid))

    async def _callback_thumbnail_gen_extract(self, chat_id: int, query, job_uuid, rescan=False):
        """Step 1: Extract reference frames from video, show selection UI."""
        from app.services.thumbnail_reference_service import thumbnail_reference_service, ThumbnailReferenceError

        await query.edit_message_text("🎬 Đang trích xuất frame tham khảo từ video...")
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return

            video_path = job.source_file_path
            if not video_path or not os.path.exists(video_path):
                # Try fallback
                job_dir = job.temp_dir or os.path.join(
                    settings.PROJECT_DATA_DIR,
                    "facebook_downloads" if job.type == "facebook_to_youtube" else "tiktok_downloads",
                    str(job.id),
                )
                video_path = os.path.join(job_dir, "source.mp4")

            if not os.path.exists(video_path):
                await query.edit_message_text("❌ Không tìm thấy file video để trích xuất frame.")
                return

            job_dir = os.path.dirname(video_path) if job.temp_dir else job_dir

        try:
            selected_frames = thumbnail_reference_service.select_best_frames(video_path, job_uuid, job_dir)
        except ThumbnailReferenceError as e:
            await query.edit_message_text(f"❌ Lỗi trích xuất frame: {e}")
            return
        except Exception as e:
            logger.exception("Frame extraction failed")
            await query.edit_message_text(f"❌ Lỗi: {e}")
            return

        if not selected_frames:
            await query.edit_message_text("⚠️ Không trích xuất được frame nào. Tiến hành tạo prompt không có reference.")
            await self._callback_thumbnail_generate(chat_id, query, job_uuid)
            return

        async with get_async_session()() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if job:
                job.thumbnail_reference_frames = json.dumps(selected_frames, ensure_ascii=False, default=str)
                job.thumbnail_status = "reference_extracted"
                await db.commit()

        text = self._format_reference_selection(selected_frames, str(job_uuid))
        reply_markup = self._build_reference_keyboard(str(job_uuid), selected_frames)

        # Send first reference frame as preview
        try:
            first_frame = selected_frames[0]["path"]
            if os.path.exists(first_frame):
                with open(first_frame, "rb") as f:
                    await query.message.reply_photo(
                        photo=f,
                        caption=f"📸 Frame #{1} — điểm: {selected_frames[0].get('score', {}).get('thumbnail_potential', 0):.1f}",
                    )
        except Exception as e:
            logger.warning("Failed to send reference frame: %s", e)

        await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_thumbnail_show_refs(self, chat_id: int, query, job_uuid):
        """Show reference frame selection UI (from prompt screen)."""
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job or not job.thumbnail_reference_frames:
                await query.answer("❌ Chưa có reference frames. Nhấn '🎨 Thumbnail AI' để quét.", show_alert=True)
                return
            try:
                ref_frames = json.loads(job.thumbnail_reference_frames)
            except (json.JSONDecodeError, TypeError):
                await query.answer("❌ Lỗi đọc reference frames.", show_alert=True)
                return
            selected = job.selected_thumbnail_reference

        text = self._format_reference_selection(ref_frames, str(job_uuid), selected)
        reply_markup = self._build_reference_keyboard(str(job_uuid), ref_frames, selected)
        await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_thumbnail_ref_select(self, chat_id: int, query, job_uuid, idx: int):
        """Select a reference frame, show it, and enable prompt generation."""
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job or not job.thumbnail_reference_frames:
                await query.answer("❌ Không có reference frames.", show_alert=True)
                return
            try:
                ref_frames = json.loads(job.thumbnail_reference_frames)
            except (json.JSONDecodeError, TypeError):
                await query.answer("❌ Lỗi đọc frames.", show_alert=True)
                return
            if idx >= len(ref_frames):
                await query.answer("❌ Frame không tồn tại.", show_alert=True)
                return
            job.selected_thumbnail_reference = idx
            await db.commit()
            ref = ref_frames[idx]

        await query.answer(f"✅ Đã chọn Frame #{idx + 1}")

        # Send the selected frame
        try:
            frame_path = ref["path"]
            if os.path.exists(frame_path):
                with open(frame_path, "rb") as f:
                    await query.message.reply_photo(
                        photo=f,
                        caption=f"✅ <b>Frame #{idx + 1} được chọn</b>\n🆔 Job: <code>{job_uuid}</code>\n👉 Nhấn '🎨 Tạo Prompt' để sinh thumbnail prompts dựa trên frame này.",
                        parse_mode="HTML",
                    )
        except Exception as e:
            logger.warning("Failed to send selected frame: %s", e)

        # Refresh the selection UI
        async with get_async_session()() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if job and job.thumbnail_reference_frames:
                ref_frames = json.loads(job.thumbnail_reference_frames)
                text = self._format_reference_selection(ref_frames, str(job_uuid), idx)
                reply_markup = self._build_reference_keyboard(str(job_uuid), ref_frames, idx)
                await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_thumbnail_generate(self, chat_id: int, query, job_uuid, regenerate=False):
        """Step 2: Generate 4 thumbnail prompts based on selected reference frame."""
        await query.edit_message_text("🎨 Đang tạo thumbnail prompts dựa trên reference frame...")
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await query.edit_message_text("❌ Job không tồn tại.")
                return
            transcript = job.transcript or ""
            title = job.ai_title or ""
            existing_prompts = None
            if regenerate and job.thumbnail_prompts:
                try:
                    existing_prompts = json.loads(job.thumbnail_prompts)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Build reference description
            reference_description = ""
            ref_info = ""
            if job.thumbnail_reference_frames and job.selected_thumbnail_reference is not None:
                try:
                    ref_frames = json.loads(job.thumbnail_reference_frames)
                    idx = job.selected_thumbnail_reference
                    if idx < len(ref_frames):
                        ref = ref_frames[idx]
                        ref_path = ref["path"]
                        desc = thumbnail_reference_service.describe_reference(ref_path, transcript, title)
                        if desc:
                            reference_description = desc
                        ref_info = f"Frame #{idx + 1}"
                except Exception as e:
                    logger.warning("Failed to describe reference: %s", e)

            if regenerate and existing_prompts:
                prompts = thumbnail_prompt_service.regenerate_prompts(transcript, title, existing_prompts, reference_description)
            else:
                prompts = thumbnail_prompt_service.generate_prompts(transcript, title, reference_description)

            job.thumbnail_prompts = json.dumps(prompts, ensure_ascii=False)
            job.thumbnail_status = "generated"
            await db.commit()

        text = self._format_thumbnail_prompts(prompts, str(job_uuid), ref_info)
        reply_markup = self._build_thumbnail_keyboard(str(job_uuid), prompts)
        await self._send_or_edit(chat_id, query.message.message_id, text, reply_markup)

    async def _callback_thumbnail_copy(self, chat_id: int, query, job_uuid, idx: int):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job or not job.thumbnail_prompts:
                await query.answer("❌ Chưa có thumbnail prompts.")
                return
            try:
                prompts = json.loads(job.thumbnail_prompts)
            except (json.JSONDecodeError, TypeError):
                await query.answer("❌ Lỗi đọc prompts.")
                return
            if idx >= len(prompts):
                await query.answer("❌ Không tìm thấy prompt.")
                return
            p = prompts[idx]
            style = p.get("style", "Unknown")
            prompt_text = p.get("prompt", "")

            # Also send reference frame info if available
            ref_info = ""
            if job.thumbnail_reference_frames and job.selected_thumbnail_reference is not None:
                try:
                    rf = json.loads(job.thumbnail_reference_frames)
                    si = job.selected_thumbnail_reference
                    if si < len(rf):
                        ref_path = rf[si]["path"]
                        ref_info = f"\n🖼 <b>Reference frame:</b> {ref_path}"
                except Exception:
                    pass

        await query.answer(f"📋 Đã copy {style}!", show_alert=False)
        msg = (
            f"📋 <b>Prompt {idx + 1}: {self._escape(style)}</b>\n\n"
            f"<code>{self._escape(prompt_text)}</code>\n"
            f"{ref_info}"
            f"\n\n🆔 Job: <code>{job_uuid}</code>"
        )
        if ref_info and os.path.exists(ref_path):
            try:
                with open(ref_path, "rb") as f:
                    await query.message.reply_photo(photo=f, caption=msg, parse_mode="HTML")
                return
            except Exception:
                pass
        await query.message.reply_text(msg, parse_mode="HTML")

    async def _callback_thumbnail_copy_all(self, chat_id: int, query, job_uuid):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job or not job.thumbnail_prompts:
                await query.answer("❌ Chưa có thumbnail prompts.")
                return
            try:
                prompts = json.loads(job.thumbnail_prompts)
            except (json.JSONDecodeError, TypeError):
                await query.answer("❌ Lỗi đọc prompts.")
                return
        await query.answer("📋 Đã sao chép tất cả prompts!", show_alert=False)
        for i, p in enumerate(prompts[:4]):
            style = p.get("style", "Unknown")
            prompt_text = p.get("prompt", "")
            await query.message.reply_text(
                f"📋 <b>Prompt {i+1}: {self._escape(style)}</b>\n\n"
                f"<code>{self._escape(prompt_text)}</code>",
                parse_mode="HTML",
            )

    async def _callback_thumbnail_preview(self, chat_id: int, query, job_uuid):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job or not job.thumbnail_path:
                await query.answer("❌ Chưa có thumbnail. Hãy upload ảnh trước.", show_alert=True)
                return
            thumb_path = job.thumbnail_path

        if not os.path.exists(thumb_path):
            await query.answer("❌ File thumbnail không tồn tại.", show_alert=True)
            return

        try:
            with open(thumb_path, "rb") as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"🖼 <b>Thumbnail Preview</b>\n🆔 Job: <code>{job_uuid}</code>",
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.warning("Failed to send thumbnail preview: %s", e)
            await query.answer("❌ Không thể gửi ảnh preview.", show_alert=True)

    async def _callback_thumbnail_skip(self, chat_id: int, query, job_uuid):
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if job:
                job.thumbnail_status = "skipped"
                await db.commit()
        await query.edit_message_text("⏭ Đã bỏ qua thumbnail. Tiến hành upload không có thumbnail.")
        await self._send_preview(chat_id, str(job_uuid))

    async def _handle_thumbnail_upload(self, chat_id: int, file_path: str):
        state = self._waiting_edit.pop(chat_id, None)
        if not state:
            return
        job_id = state["job_id"]
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            job_dir = job.temp_dir or os.path.join(
                settings.PROJECT_DATA_DIR,
                "facebook_downloads" if job.type == "facebook_to_youtube" else "tiktok_downloads",
                str(job.id),
            )
            os.makedirs(job_dir, exist_ok=True)
            thumb_dest = os.path.join(job_dir, "thumbnail.jpg")
            import shutil
            shutil.move(file_path, thumb_dest)
            job.thumbnail_path = thumb_dest
            job.thumbnail_status = "approved"
            await db.commit()

        await telegram_bot.application.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Đã lưu thumbnail! Job: <code>{job_id}</code>\n"
                 f"📁 {thumb_dest}\n\n"
                 f"Dùng /preview_thumb {job_id} để xem.",
            parse_mode="HTML",
        )
        # Return to thumbnail screen
        async with get_async_session()() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if job and job.thumbnail_prompts:
                try:
                    prompts = json.loads(job.thumbnail_prompts)
                    ref_info = ""
                    if job.thumbnail_reference_frames and job.selected_thumbnail_reference is not None:
                        ref_info = f"Frame #{job.selected_thumbnail_reference + 1}"
                    text = self._format_thumbnail_prompts(prompts, str(job_id), ref_info)
                    reply_markup = self._build_thumbnail_keyboard(str(job_id), prompts)
                    await telegram_bot.application.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                    )
                except Exception:
                    pass

    async def _handle_photo(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        chat_id = upd.effective_chat.id
        if not self._check_admin(chat_id):
            return
        if chat_id not in self._waiting_edit:
            return
        state = self._waiting_edit.get(chat_id)
        if not state or state.get("field") != "thumbnail_upload":
            return
        photo = upd.message.photo[-1]
        file = await photo.get_file()
        tmp_path = f"/tmp/thumb_{state['job_id']}_{photo.file_id}.jpg"
        await file.download_to_drive(tmp_path)
        await self._handle_thumbnail_upload(chat_id, tmp_path)

    async def _projects(self, update: object, context: object):
        from telegram import Update
        upd: Update = update
        if not self._check_admin(upd.effective_chat.id):
            return
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select, desc
            result = await db.execute(
                select(VideoJob).order_by(desc(VideoJob.created_at)).limit(10)
            )
            jobs = list(result.scalars().all())
        if not jobs:
            await upd.message.reply_text("📭 Chưa có project nào.")
            return
        lines = ["📋 <b>Recent Projects</b>", "━━━━━━━━━━━━━━━━━━"]
        for j in jobs:
            title = (j.ai_title or "Untitled")[:30]
            sid = str(j.id)[:8]
            status_icon = "✅" if j.status == "completed" else "🔄" if j.status in ("processing", "pending") else "❌"
            lines.append(f"{status_icon} <code>{sid}</code> — {self._escape(title)}")
        await upd.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _subs(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        if not self._check_admin(upd.effective_chat.id):
            return
        if not ctx.args:
            await upd.message.reply_text("⚠️ Dùng: /subs &lt;job_id&gt;")
            return
        try:
            job_uuid = UUID(ctx.args[0])
        except ValueError:
            await upd.message.reply_text("⚠️ Job ID không hợp lệ.")
            return
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await upd.message.reply_text("❌ Job không tồn tại.")
                return
            from app.models.subtitle_cue import SubtitleCue
            cues_result = await db.execute(
                select(SubtitleCue).where(SubtitleCue.job_id == job_uuid).order_by(SubtitleCue.cue_number)
            )
            cues = list(cues_result.scalars().all())
        if not cues:
            await upd.message.reply_text("📭 Job này chưa có subtitle cues.")
            return
        total = len(cues)
        cps_warn = sum(1 for c in cues if (c.cps or 0) > 22)
        cps_bad = sum(1 for c in cues if (c.cps or 0) > 35)
        lines = [
            f"📝 <b>Subtitles</b>  ·  <code>{str(job_uuid)[:8]}</code>",
            "━━━━━━━━━━━━━━━━━━",
            f"📄 Total cues: {total}",
            f"⚠️ CPS &gt;22: {cps_warn}",
            f"❌ CPS &gt;35: {cps_bad}",
            "",
            f"📊 Translation: {self._status_line('Status', job.translation_status or 'pending')}",
        ]
        await upd.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _tts_status(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        if not self._check_admin(upd.effective_chat.id):
            return
        if not ctx.args:
            await upd.message.reply_text("⚠️ Dùng: /tts &lt;job_id&gt;")
            return
        try:
            job_uuid = UUID(ctx.args[0])
        except ValueError:
            await upd.message.reply_text("⚠️ Job ID không hợp lệ.")
            return
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            from app.models.tts_segment import TtsSegment
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await upd.message.reply_text("❌ Job không tồn tại.")
                return
            segs_result = await db.execute(
                select(TtsSegment).where(TtsSegment.job_id == job_uuid)
            )
            segs = list(segs_result.scalars().all())
        total_segs = len(segs)
        done_segs = sum(1 for s in segs if s.status == "completed")
        total_dur = sum(s.duration or 0 for s in segs)
        lines = [
            f"🔊 <b>TTS Status</b>  ·  <code>{str(job_uuid)[:8]}</code>",
            "━━━━━━━━━━━━━━━━━━",
            f"🎵 Segments: {done_segs}/{total_segs}",
            f"⏱ Total audio: {total_dur:.1f}s",
            f"📊 {self._status_line('Status', job.tts_status or 'pending')}",
        ]
        await upd.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _render_status(self, update: object, context: object):
        from telegram import Update
        from telegram.ext import ContextTypes
        upd: Update = update
        ctx: ContextTypes.DEFAULT_TYPE = context
        if not self._check_admin(upd.effective_chat.id):
            return
        if not ctx.args:
            await upd.message.reply_text("⚠️ Dùng: /render &lt;job_id&gt;")
            return
        try:
            job_uuid = UUID(ctx.args[0])
        except ValueError:
            await upd.message.reply_text("⚠️ Job ID không hợp lệ.")
            return
        async_session = get_async_session()
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_uuid))
            job = result.scalar_one_or_none()
            if not job:
                await upd.message.reply_text("❌ Job không tồn tại.")
                return
        render_modes = []
        if job.rendered_hardsub_path:
            render_modes.append("🎬 Hardsub")
        if job.rendered_softsub_path:
            render_modes.append("📺 Softsub")
        if job.rendered_audio_path:
            render_modes.append("🔊 Voice-only")
        lines = [
            f"🎞 <b>Render Status</b>  ·  <code>{str(job_uuid)[:8]}</code>",
            "━━━━━━━━━━━━━━━━━━",
            f"📊 {self._status_line('Status', job.render_status or 'pending')}",
        ]
        if render_modes:
            lines.append(f"✅ Rendered: {', '.join(render_modes)}")
        else:
            lines.append("📭 Chưa render")
        if job.rendered_hardsub_path and os.path.exists(job.rendered_hardsub_path):
            fsize = os.path.getsize(job.rendered_hardsub_path)
            lines.append(f"📁 Size: {fsize / 1024 / 1024:.1f}MB")
        await upd.message.reply_text("\n".join(lines), parse_mode="HTML")

    def build_application(self) -> Optional[object]:
        if not self.enabled:
            logger.warning("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID)")
            return None
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
        application = Application.builder().token(self._token).build()
        application.add_handler(CommandHandler("start", self._start))
        application.add_handler(CommandHandler("help", self._help))
        application.add_handler(CommandHandler("status", self._status))
        application.add_handler(CommandHandler("glossary", self._glossary_help))
        application.add_handler(CommandHandler("add_glossary", self._add_glossary))
        application.add_handler(CommandHandler("list_glossary", self._list_glossary))
        application.add_handler(CommandHandler("delete_glossary", self._delete_glossary))
        application.add_handler(CommandHandler("cancel_edit", self._cancel_edit))
        application.add_handler(CommandHandler("projects", self._projects))
        application.add_handler(CommandHandler("subs", self._subs))
        application.add_handler(CommandHandler("tts", self._tts_status))
        application.add_handler(CommandHandler("render", self._render_status))
        application.add_handler(CallbackQueryHandler(self._handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))
        application.add_error_handler(self._error_handler)
        return application

    async def start_polling(self, max_retries: int = 5):
        self.configure()
        self.application = self.build_application()
        if not self.application:
            return
        await self.application.initialize()
        await self.application.start()
        await self._set_menu_commands()
        from telegram import TelegramError
        for attempt in range(max_retries):
            try:
                await self.application.updater.start_polling(drop_pending_updates=True)
                logger.info("Telegram bot polling started")
                return
            except TelegramError as e:
                logger.warning("Bot polling attempt %d/%d failed: %s", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    logger.error("Bot polling failed after %d attempts: %s", max_retries, e)

    async def _error_handler(self, update, context):
        from telegram import TelegramError
        error = context.error
        if isinstance(error, TelegramError):
            logger.warning("Telegram error: %s", error)

    async def _set_menu_commands(self, app=None):
        from telegram import BotCommand, MenuButtonWebApp, WebAppInfo
        bot = (app or self.application).bot
        try:
            commands = [
                BotCommand("start", "Khởi động bot"),
                BotCommand("help", "Hướng dẫn sử dụng"),
                BotCommand("status", "Kiểm tra trạng thái job"),
                BotCommand("glossary", "Hướng dẫn glossary"),
                BotCommand("add_glossary", "Thêm entry glossary"),
                BotCommand("list_glossary", "Xem danh sách glossary"),
                BotCommand("delete_glossary", "Xóa entry glossary"),
                BotCommand("cancel_edit", "Hủy thao tác đang chỉnh sửa"),
                BotCommand("projects", "Xem danh sách projects"),
                BotCommand("subs", "Xem trạng thái subtitles"),
                BotCommand("tts", "Xem trạng thái TTS"),
                BotCommand("render", "Xem trạng thái render"),
            ]
            await bot.set_my_commands(commands)
            logger.info("Bot menu commands set")

            mini_app_url = settings.MINI_APP_URL or "https://telegram-mini-green.vercel.app"
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="VidLocal Studio 🎬",
                    web_app=WebAppInfo(url=mini_app_url),
                )
            )
            logger.info("Mini App menu button set to %s", mini_app_url)
        except Exception as e:
            logger.warning("Failed to set menu commands: %s", e)

    async def stop_polling(self):
        if self.application:
            logger.info("Telegram bot polling stopped")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


telegram_bot = TelegramBotService()
