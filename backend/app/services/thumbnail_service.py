import json
import re
import logging
from typing import Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from app.config import settings
from app.services.base_ai_service import BaseAIService, RetryExhaustedError

logger = logging.getLogger(__name__)

THUMBNAIL_PROMPT_TEMPLATE = """Bạn là chuyên gia thiết kế thumbnail YouTube. Dựa vào transcript, SEO title, và REFERENCE FRAME bên dưới, hãy tạo 4 prompt thumbnail khác nhau theo các phong cách khác nhau.

## Transcript:
{transcript}

## SEO Title:
{title}

## Reference Frame Description (character & scene from the actual video):
{reference_description}

## QUAN TRỌNG — KHÔNG ĐƯỢC TẠO NHÂN VẬT NGẪU NHIÊN:
- Use the character from the reference frame as the main subject.
- Keep the character's face, hairstyle, outfit, and expression CONSISTENT with the reference.
- Do NOT invent a different person or change the character's appearance.
- The thumbnail MUST be based on this exact character from the video.
- If the reference has a specific scene background, preserve the mood/colors.

## Quy tắc chung cho tất cả prompt:
- Ảnh 16:9, cinematic, high contrast, dramatic lighting
- Bold Vietnamese text, không watermark, không extra text ngoài main text
- Clear subject, màu sắc nổi bật, dễ đọc
- Mỗi prompt là 1 câu mô tả chi tiết bằng tiếng Anh (dùng để generate image)
- Ghi rõ main character appearance in the prompt based on reference

## 4 phong cách:

1. **Drama** - Kịch tính, căng thẳng, high contrast, biểu cảm nhân vật mạnh, màu tối - đỏ
   Output format: {{"style": "Drama", "prompt": "..."}}

2. **Review phim** - Giống poster phim điện ảnh, cinematic composition, depth of field, chân dung nhân vật trung tâm
   Output format: {{"style": "Review phim", "prompt": "..."}}

3. **Xianxia/Anime** - Phong cách tiên hiệp/anime, fantasy lighting, ethereal glow, mây mù, thần thái nhân vật
   Output format: {{"style": "Xianxia/Anime", "prompt": "..."}}

4. **Viral CTR** - Tối ưu click rate, màu sắc chói, surprise face, chữ to đùng, composition rối mắt nhưng thu hút
   Output format: {{"style": "Viral CTR", "prompt": "..."}}

## QUAN TRỌNG:
- Mỗi prompt bằng tiếng Anh, 1-2 câu, đủ chi tiết để generate ảnh 1280x720
- Phải mô tả nhân vật dựa trên reference frame, KHÔNG tự ý thay đổi
- KHÔNG thêm text không cần thiết
- Trả về JSON array thuần, không markdown, không preamble

Output format:
[
  {{"style": "Drama", "prompt": "A cinematic 16:9 thumbnail featuring [character from reference]..."}},
  {{"style": "Review phim", "prompt": "A movie poster style portrait of [character from reference]..."}},
  {{"style": "Xianxia/Anime", "prompt": "An ethereal fantasy scene with [character from reference]..."}},
  {{"style": "Viral CTR", "prompt": "A vibrant clickbait composition featuring [character from reference]..."}}
]"""

FALLBACK_PROMPTS = [
    {"style": "Drama", "prompt": "Dramatic cinematic shot, high contrast, intense lighting, bold text overlay, 16:9 thumbnail, no watermark"},
    {"style": "Review phim", "prompt": "Movie poster style composition, cinematic depth of field, centered character portrait, dramatic lighting, 16:9"},
    {"style": "Xianxia/Anime", "prompt": "Fantasy ethereal scene, misty mountains, glowing aura, anime style character, dramatic sky, 16:9"},
    {"style": "Viral CTR", "prompt": "Vibrant colors, surprised expression, bold text in center, high energy composition, eye-catching, 16:9"},
]


class ThumbnailPromptError(Exception):
    pass


class ThumbnailPromptService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="ThumbnailPrompt",
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            retries=max(settings.GEMINI_RETRIES, 0),
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=30.0,
        )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_name = settings.AI_MODEL or "gemini-1.5-flash-latest"
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 2048,
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

    def _parse_prompts(self, raw_text: str) -> list:
        json_match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if not json_match:
            raise ValueError("AI response does not contain valid JSON array")
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from AI: {e}")
        if not isinstance(data, list) or len(data) != 4:
            raise ValueError(f"Expected 4 prompts, got {len(data) if isinstance(data, list) else 'not a list'}")
        for item in data:
            if "style" not in item or "prompt" not in item:
                raise ValueError("Each prompt must have 'style' and 'prompt' keys")
            item["prompt"] = str(item["prompt"])[:500]
        return data

    def generate_prompts(self, transcript: str, title: str = "", reference_description: str = "") -> list:
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript, using fallback thumbnail prompts")
            return list(FALLBACK_PROMPTS)
        prompt = THUMBNAIL_PROMPT_TEMPLATE.format(
            transcript=transcript[:8000],
            title=title[:200] if title else "Video",
            reference_description=reference_description[:1500] if reference_description else "No reference frame available. Create a generic cinematic scene.",
        )
        try:
            raw_text = self.call_with_retry(self._generate, prompt)
        except RetryExhaustedError as e:
            logger.error("Thumbnail prompt generation failed after retries: %s", e)
            return list(FALLBACK_PROMPTS)
        except Exception as e:
            logger.error("Thumbnail prompt generation failed: %s", e)
            return list(FALLBACK_PROMPTS)
        try:
            return self._parse_prompts(raw_text)
        except ValueError as e:
            logger.error("Failed to parse thumbnail prompts: %s", e)
            return list(FALLBACK_PROMPTS)

    def regenerate_prompts(self, transcript: str, title: str = "", previous: Optional[list] = None, reference_description: str = "") -> list:
        if not transcript or not transcript.strip():
            return list(FALLBACK_PROMPTS)
        prompt = THUMBNAIL_PROMPT_TEMPLATE.format(
            transcript=transcript[:8000],
            title=title[:200] if title else "Video",
            reference_description=reference_description[:1500] if reference_description else "No reference frame available. Create a generic cinematic scene.",
        )
        if previous:
            prompt += f"\n\nLần trước bạn đã tạo các prompt này. Hãy tạo phiên bản KHÁC, sáng tạo hơn:\n{json.dumps(previous, ensure_ascii=False, indent=2)}"
        try:
            raw_text = self.call_with_retry(self._generate, prompt)
        except RetryExhaustedError:
            return list(FALLBACK_PROMPTS)
        except Exception:
            return list(FALLBACK_PROMPTS)
        try:
            return self._parse_prompts(raw_text)
        except ValueError:
            return list(FALLBACK_PROMPTS)


thumbnail_prompt_service = ThumbnailPromptService()
