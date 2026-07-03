import json
import re
import logging
from typing import List, Optional, Dict, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.models.video_job import VideoJob
from app.models.character_glossary_draft import CharacterGlossaryDraft, CharacterGlossaryItem
from app.services.base_ai_service import BaseAIService, RetryExhaustedError

logger = logging.getLogger(__name__)

CHARACTER_EXTRACTION_PROMPT = """Bạn là chuyên gia phân tích nội dung video. Dựa vào transcript bên dưới, hãy trích xuất tất cả nhân vật, tổ chức, địa danh và thuật ngữ quan trọng.

Đối với mỗi thực thể, hãy đề xuất tên tiếng Việt phù hợp để dịch thuật nhất quán.

Transcript:
{transcript}

Yêu cầu:
1. Chỉ trích xuất các thực thể CÓ THẬT trong transcript, KHÔNG bịa đặt
2. source_name: tên gốc trong transcript
3. suggested_vietnamese_name: tên tiếng Việt đề xuất (giữ nguyên nếu là tên Việt/Anh phổ biến)
4. aliases: các tên gọi khác của cùng thực thể trong transcript
5. Nếu không chắc chắn về bản dịch, giữ nguyên source_name làm target_name

Trả về JSON thuần, không markdown, không preamble:

{{
  "characters": [
    {{
      "source_name": "...",
      "suggested_vietnamese_name": "...",
      "aliases": ["...", "..."],
      "role": "vai trò trong câu chuyện",
      "family_clan": "họ/gia tộc (nếu có)",
      "gender": "male|female|unknown",
      "relationships": ["mô tả mối quan hệ"],
      "pronoun_style": "cách xưng hô gợi ý",
      "notes": "ghi chú thêm"
    }}
  ],
  "organizations": [
    {{
      "source_name": "...",
      "suggested_vietnamese_name": "...",
      "aliases": ["...", "..."],
      "notes": "..."
    }}
  ],
  "places": [
    {{
      "source_name": "...",
      "suggested_vietnamese_name": "...",
      "aliases": ["...", "..."],
      "notes": "..."
    }}
  ],
  "terms": [
    {{
      "source_name": "...",
      "suggested_vietnamese_name": "...",
      "aliases": ["...", "..."],
      "notes": "..."
    }}
  ]
}}

Nếu không tìm thấy thực thể nào, trả về mảng rỗng cho mỗi danh mục."""


class CharacterExtractionService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="CharacterExtraction",
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            retries=max(settings.GEMINI_RETRIES, 0),
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=30.0,
        )
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_name = settings.AI_MODEL or "gemini-1.5-flash-latest"
        generation_config = {
            "temperature": 0.2,
            "max_output_tokens": 8192,
        }
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
        )

    def _generate(self, prompt: str) -> str:
        from google.api_core import exceptions as google_exceptions
        retryable = (
            google_exceptions.DeadlineExceeded,
            google_exceptions.ServiceUnavailable,
            google_exceptions.ResourceExhausted,
            google_exceptions.Aborted,
        )
        try:
            response = self.model.generate_content(prompt, request_options={"timeout": self.timeout})
            return response.text.strip()
        except retryable:
            raise
        except Exception as e:
            raise RuntimeError(f"Gemini non-retryable error: {e}") from e

    def _parse_extraction(self, raw_text: str) -> dict:
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_match:
            raise ValueError("AI response does not contain valid JSON")
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from AI: {e}")
        for key in ("characters", "organizations", "places", "terms"):
            if key not in data:
                data[key] = []
            if not isinstance(data[key], list):
                data[key] = []
        return data

    def extract(self, transcript: str) -> dict:
        if not transcript or not transcript.strip():
            return {"characters": [], "organizations": [], "places": [], "terms": []}
        prompt = CHARACTER_EXTRACTION_PROMPT.format(
            transcript=transcript[:12000]
        )
        try:
            raw_text = self.call_with_retry(self._generate, prompt)
        except RetryExhaustedError as e:
            logger.error("Character extraction failed after retries: %s", e)
            return {"characters": [], "organizations": [], "places": [], "terms": []}
        except Exception as e:
            logger.error("Character extraction failed: %s", e)
            return {"characters": [], "organizations": [], "places": [], "terms": []}
        try:
            return self._parse_extraction(raw_text)
        except ValueError as e:
            logger.error("Failed to parse extraction: %s", e)
            return {"characters": [], "organizations": [], "places": [], "terms": []}

    async def save_draft(self, job_id: UUID, extraction_data: dict) -> Tuple[CharacterGlossaryDraft, List[CharacterGlossaryItem]]:
        async_session = get_async_session()
        async with async_session() as db:
            draft = CharacterGlossaryDraft(
                job_id=job_id,
                raw_json=extraction_data,
                status="pending",
            )
            db.add(draft)
            await db.flush()

            items = []
            all_entries = []
            for cat in ("characters", "organizations", "places", "terms"):
                for entry in extraction_data.get(cat, []):
                    all_entries.append((cat, entry))
            for cat, entry in all_entries:
                item = CharacterGlossaryItem(
                    job_id=job_id,
                    draft_id=draft.id,
                    category=cat,
                    source_name=entry.get("source_name", "").strip(),
                    target_name=entry.get("suggested_vietnamese_name", entry.get("source_name", "")).strip(),
                    aliases=entry.get("aliases", []),
                    role=entry.get("role"),
                    family_clan=entry.get("family_clan"),
                    gender=entry.get("gender"),
                    relationships=entry.get("relationships", []),
                    pronoun_style=entry.get("pronoun_style"),
                    notes=entry.get("notes"),
                    approved=True,
                )
                db.add(item)
                items.append(item)
            await db.flush()

            await db.execute(
                select(VideoJob).where(VideoJob.id == job_id)
            )
            await db.commit()

            for item in items:
                await db.refresh(item)
            await db.refresh(draft)

            return draft, items

    async def load_approved_items(self, job_id: UUID) -> List[CharacterGlossaryItem]:
        async_session = get_async_session()
        async with async_session() as db:
            result = await db.execute(
                select(CharacterGlossaryItem)
                .where(CharacterGlossaryItem.job_id == job_id, CharacterGlossaryItem.approved.is_(True))
                .order_by(CharacterGlossaryItem.source_name)
            )
            return list(result.scalars().all())

    def items_to_glossary_block(self, items: List[CharacterGlossaryItem]) -> str:
        if not items:
            return ""
        lines = ["\n## Character Name Glossary (BẮT BUỘC tuân theo):"]
        groups = {"character": [], "organization": [], "place": [], "term": []}
        for item in items:
            cat = item.category or "character"
            groups.get(cat, groups["character"]).append(item)
        for cat, label in [("character", "Nhân vật"), ("organization", "Tổ chức"), ("place", "Địa danh"), ("term", "Thuật ngữ")]:
            if groups.get(cat):
                lines.append(f"\n### {label}:")
                for item in groups[cat]:
                    names = [item.source_name]
                    if item.aliases:
                        names.extend(str(a) for a in item.aliases)
                    names_str = ", ".join(names)
                    parts = [f"  {names_str} → {item.target_name}"]
                    if item.role:
                        parts.append(f"  Vai trò: {item.role}")
                    if item.family_clan:
                        parts.append(f"  Gia tộc: {item.family_clan}")
                    if item.gender:
                        parts.append(f"  Giới tính: {item.gender}")
                    if item.pronoun_style:
                        parts.append(f"  Xưng hô: {item.pronoun_style}")
                    if item.notes:
                        parts.append(f"  Ghi chú: {item.notes}")
                    lines.extend(parts)
                    lines.append("")
        lines.append("QUAN TRỌNG: Bạn PHẢI dùng target_name ở trên mỗi khi gặp các tên này. KHÔNG được dùng tên gốc.")
        lines.append("Nếu có tên nhân vật mới xuất hiện không có trong danh sách, hãy giữ nguyên tên gốc và báo lại.")
        return "\n".join(lines)

    def format_draft_for_review(self, draft: CharacterGlossaryDraft, items: List[CharacterGlossaryItem]) -> str:
        if not items:
            return "📭 Không phát hiện nhân vật/tổ chức/địa danh nào."
        lines = ["📋 <b>Danh sách thực thể phát hiện:</b>\n"]
        groups = {"character": "Nhân vật", "organization": "Tổ chức", "place": "Địa danh", "term": "Thuật ngữ"}
        for cat_key, cat_label in groups.items():
            cat_items = [i for i in items if (i.category or "character") == cat_key]
            if not cat_items:
                continue
            lines.append(f"<b>{cat_label}:</b>")
            for idx, item in enumerate(cat_items, 1):
                lines.append(
                    f"{idx}. {item.source_name} → {item.target_name}"
                )
                if item.role:
                    lines.append(f"   Vai trò: {item.role}")
                if item.aliases:
                    aliases_str = ", ".join(str(a) for a in item.aliases)
                    lines.append(f"   Tên gọi khác: {aliases_str}")
                if item.family_clan:
                    lines.append(f"   Gia tộc: {item.family_clan}")
                if item.gender:
                    gender_label = {"male": "Nam", "female": "Nữ", "unknown": "Không rõ"}.get(item.gender, item.gender)
                    lines.append(f"   Giới tính: {gender_label}")
                if item.pronoun_style:
                    lines.append(f"   Xưng hô: {item.pronoun_style}")
                if item.notes:
                    lines.append(f"   Ghi chú: {item.notes}")
                lines.append("")
            lines.append("")
        return "\n".join(lines)


character_extraction_service = CharacterExtractionService()
