import json
import re
import logging
from typing import Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from app.config import settings
from app.services.base_ai_service import BaseAIService, RetryExhaustedError

logger = logging.getLogger(__name__)

def _glossary_items_to_entries(items):
    result = []
    for item in items:
        class _Entry:
            source_name = item.source_name
            target_name = item.target_name
            aliases = item.aliases or []
            gender = item.gender
            role = item.role
            pronoun_style = item.pronoun_style
            note = item.notes
        result.append(_Entry())
    return result

SEO_METADATA_PROMPT_TEMPLATE = """Bạn là chuyên gia SEO YouTube. Dựa vào transcript và metadata gốc bên dưới, hãy tạo SEO metadata chuẩn cho video.

## Transcript:
{transcript}

## Metadata gốc (nếu có):
{source_metadata}

## Yêu cầu:
1. Title: tối đa 90 ký tự, chuẩn SEO, hấp dẫn nhưng KHÔNG giật tít
2. Description: 2-4 đoạn, tóm tắt nội dung, có kêu gọi hành động nhẹ nhàng
3. Tags: 10-20 từ khóa liên quan đến nội dung
4. Hashtags: 5-12 hashtag, viết liền không dấu, có dấu #
5. Category: chọn 1 category YouTube phù hợp (VD: Education, Entertainment, News & Politics, Howto & Style, Science & Technology, Music, Gaming, Sports, Travel & Events, People & Blogs, Film & Animation, Nonprofits & Activism)
6. Summary: 1-2 câu tóm tắt nội dung
7. Hook: 1 câu mở đầu hấp dẫn để giữ chân người xem
8. Language: ngôn ngữ chính của video (vi|en|zh|other)
9. Risk flags: mảng các cảnh báo nếu có dấu hiệu vi phạm bản quyền, reup, phim ảnh, nhạc có bản quyền. Chỉ thêm flag nếu transcript có dấu hiệu RÕ RÀNG. Flag hợp lệ: "copyright_audio", "copyright_video", "movie_clip", "reup", "music_copyright"

## QUAN TRỌNG:
- KHÔNG bịa nội dung không có trong transcript
- Nếu transcript quá ngắn hoặc không rõ ràng, tạo metadata an toàn, chung chung
- Không spam keyword
- Nếu nội dung là tiếng Việt, ưu tiên tạo title/description bằng tiếng Việt
- Nếu nội dung là tiếng Anh hoặc Trung, có thể tạo title tiếng Việt để dễ tìm kiếm
- Chỉ đánh dấu risk_flags nếu có dấu hiệu RÕ RÀNG, KHÔNG suy diễn
- Trả về JSON thuần, không markdown, không preamble

Output format:
{{
  "title": "...",
  "description": "...",
  "tags": ["...", "..."],
  "hashtags": ["...", "..."],
  "category": "...",
  "summary": "...",
  "hook": "...",
  "language": "vi|en|zh|other",
  "risk_flags": []
}}"""

FALLBACK_METADATA = {
    "title": "Video từ Facebook",
    "description": "Video được chia sẻ từ Facebook.",
    "tags": ["video", "facebook"],
    "hashtags": ["#video", "#facebook"],
    "category": "People & Blogs",
    "summary": "Video từ Facebook.",
    "hook": "Xem video này!",
    "language": "vi",
    "risk_flags": [],
}


class SEOMetadataError(Exception):
    pass


class SEOMetadataService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="SEOMetadata",
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            retries=max(settings.GEMINI_RETRIES, 0),
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=30.0,
        )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_name = settings.AI_MODEL or "gemini-1.5-flash-latest"
        generation_config = {
            "temperature": 0.3,
            "max_output_tokens": 4096,
        }
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
        )

    def _generate(self, prompt: str) -> str:
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

    def _parse_metadata(self, raw_text: str) -> dict:
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_match:
            raise ValueError("AI response does not contain valid JSON")
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from AI: {e}")
        required_keys = ["title", "description", "tags", "hashtags", "category", "summary", "hook", "language", "risk_flags"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        data["title"] = str(data["title"])[:90]
        if not isinstance(data["tags"], list):
            data["tags"] = []
        if not isinstance(data["hashtags"], list):
            data["hashtags"] = []
        if not isinstance(data["risk_flags"], list):
            data["risk_flags"] = []
        return data

    def _apply_glossary_to_meta(self, meta: dict, entries: Optional[list] = None) -> dict:
        try:
            from app.services.glossary_service import glossary_service
            if entries is None:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                entries = loop.run_until_complete(glossary_service.get_glossary())
                loop.close()
            if not entries:
                return meta
            meta["title"] = glossary_service.apply_glossary_to_text(meta["title"], entries)
            meta["description"] = glossary_service.apply_glossary_to_text(meta["description"], entries)
            meta["summary"] = glossary_service.apply_glossary_to_text(meta["summary"], entries)
            meta["hook"] = glossary_service.apply_glossary_to_text(meta["hook"], entries)
        except Exception as e:
            logger.warning("Failed to apply glossary to SEO metadata: %s", e)
        return meta

    def _apply_glossary_to_transcript(self, transcript: str, entries: Optional[list] = None) -> str:
        try:
            from app.services.glossary_service import glossary_service
            if entries is None:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                entries = loop.run_until_complete(glossary_service.get_glossary())
                loop.close()
            if entries:
                return glossary_service.apply_glossary_to_text(transcript, entries)
        except Exception as e:
            logger.warning("Failed to apply glossary to transcript: %s", e)
        return transcript

    def generate(self, transcript: str, source_metadata: Optional[dict] = None, glossary_items: Optional[list] = None) -> dict:
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript, using fallback metadata")
            return dict(FALLBACK_METADATA)
        if glossary_items:
            owned_entries = _glossary_items_to_entries(glossary_items)
            processed_transcript = self._apply_glossary_to_transcript(transcript, owned_entries)
        else:
            processed_transcript = self._apply_glossary_to_transcript(transcript)
        prompt = SEO_METADATA_PROMPT_TEMPLATE.format(
            transcript=processed_transcript[:10000],
            source_metadata=json.dumps(source_metadata or {}, ensure_ascii=False),
        )
        try:
            raw_text = self.call_with_retry(self._generate, prompt)
        except RetryExhaustedError as e:
            logger.error("AI metadata generation failed after retries: %s", e)
            return dict(FALLBACK_METADATA)
        except Exception as e:
            logger.error("AI metadata generation failed: %s", e)
            return dict(FALLBACK_METADATA)
        try:
            meta = self._parse_metadata(raw_text)
            if glossary_items:
                owned_entries = _glossary_items_to_entries(glossary_items)
                meta = self._apply_glossary_to_meta(meta, owned_entries)
            else:
                meta = self._apply_glossary_to_meta(meta)
            return meta
        except ValueError as e:
            logger.error("Failed to parse AI response: %s", e)
            return dict(FALLBACK_METADATA)

    def regenerate(self, transcript: str, source_metadata: Optional[dict] = None, previous: Optional[dict] = None, glossary_items: Optional[list] = None) -> dict:
        if not transcript or not transcript.strip():
            return dict(FALLBACK_METADATA)
        if glossary_items:
            owned_entries = _glossary_items_to_entries(glossary_items)
            processed_transcript = self._apply_glossary_to_transcript(transcript, owned_entries)
        else:
            processed_transcript = self._apply_glossary_to_transcript(transcript)
        prompt = SEO_METADATA_PROMPT_TEMPLATE.format(
            transcript=processed_transcript[:10000],
            source_metadata=json.dumps(source_metadata or {}, ensure_ascii=False),
        )
        prompt += f"\n\nLần trước bạn đã tạo metadata này, hãy tạo phiên bản KHÁC, sáng tạo hơn:\n{json.dumps(previous, ensure_ascii=False, indent=2)}"
        try:
            raw_text = self.call_with_retry(self._generate, prompt)
        except RetryExhaustedError:
            return dict(FALLBACK_METADATA)
        except Exception:
            return dict(FALLBACK_METADATA)
        try:
            meta = self._parse_metadata(raw_text)
            if glossary_items:
                owned_entries = _glossary_items_to_entries(glossary_items)
                meta = self._apply_glossary_to_meta(meta, owned_entries)
            else:
                meta = self._apply_glossary_to_meta(meta)
            return meta
        except ValueError:
            return dict(FALLBACK_METADATA)


seo_metadata_service = SEOMetadataService()
