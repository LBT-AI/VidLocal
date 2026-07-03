import json
import re
from typing import List
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from app.config import settings
from app.services.cps_service import cps_service
from app.services.srt_service import SRTCue
from app.services.base_ai_service import BaseAIService, RetryExhaustedError


class GeminiService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="Gemini",
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            retries=max(settings.GEMINI_RETRIES, 0),
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=30.0,
        )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        generation_config = {
            "temperature": 0.3,
            "max_output_tokens": 8192,
        }
        self.model = genai.GenerativeModel(
            "gemini-1.5-pro-latest",
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

    def translate_cues(self, cues: List[SRTCue], glossary_entries: list = None) -> List[SRTCue]:
        BATCH_SIZE = 30
        all_translated = []
        for i in range(0, len(cues), BATCH_SIZE):
            batch = cues[i:i + BATCH_SIZE]
            translated = self._translate_batch(batch, glossary_entries)
            all_translated.extend(translated)
        return all_translated

    def _translate_batch(self, cues: List[SRTCue], glossary_entries: list = None) -> List[SRTCue]:
        input_json = [
            {"cue_index": c.index, "start_ms": c.start_ms, "end_ms": c.end_ms, "zh_text": c.text}
            for c in cues
        ]
        glossary_block = ""
        if glossary_entries:
            from app.services.glossary_service import glossary_service
            glossary_block = glossary_service.build_glossary_block(glossary_entries)
        prompt = f"""You are a professional subtitle translator. Translate the following Chinese subtitles to natural Vietnamese.

Rules:
- Preserve cue_index and timestamps exactly.
- Translate naturally, do not add explanations.
- Max 2 lines per cue.
- Target CPS <= 22 characters/second.
- Do not merge or split cues.
{glossary_block}
- Output ONLY valid JSON array, no markdown, no preamble.

Input:
{json.dumps(input_json, ensure_ascii=False, indent=2)}

Output format:
[
  {{"cue_index": 1, "start_ms": 1200, "end_ms": 4500, "vi_text": "..."}},
  ...
]"""
        try:
            raw_text = self.call_with_retry(self._generate, prompt)
        except RetryExhaustedError as e:
            raise RuntimeError(f"Gemini translation batch failed: {e}") from e
        json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if not json_match:
            raise ValueError("Gemini did not return valid JSON array")
        result = json.loads(json_match.group())
        translated = []
        for item in result:
            translated.append(SRTCue(
                index=item["cue_index"],
                start_ms=item["start_ms"],
                end_ms=item["end_ms"],
                text=item["vi_text"].strip()
            ))
        return translated

    def shorten_cue(self, cue: SRTCue, max_chars: int) -> str:
        prompt = f"""Rút gọn câu phụ đề tiếng Việt sau đây, giữ nguyên ý nghĩa chính, tối đa {max_chars} ký tự (không tính dấu cách và xuống dòng). Chỉ trả về text đã rút gọn, không giải thích.

"{cue.text}"
"""
        try:
            return self.call_with_retry(self._generate, prompt).strip('"').strip("'")
        except RetryExhaustedError as e:
            raise RuntimeError(f"Gemini shorten_cue failed: {e}") from e

    def auto_fix_cps(self, cue: SRTCue) -> SRTCue:
        result = cps_service.check_cps(cue.text, cue.start_ms, cue.end_ms)
        cps = result["cps"]
        if cps <= cps_service.MAX_CPS:
            return cue
        if cps_service.MAX_CPS < cps <= cps_service.WARNING_CPS:
            text = cps_service.split_lines(cue.text)
            new_result = cps_service.check_cps(text, cue.start_ms, cue.end_ms)
            if new_result["cps"] <= cps_service.WARNING_CPS:
                return SRTCue(index=cue.index, start_ms=cue.start_ms, end_ms=cue.end_ms, text=text)
        if cps <= cps_service.CRITICAL_CPS:
            max_chars = int(cps_service.MAX_CPS * ((cue.end_ms - cue.start_ms) / 1000))
            shortened = self.shorten_cue(cue, max_chars)
            new_result = cps_service.check_cps(shortened, cue.start_ms, cue.end_ms)
            if new_result["cps"] <= cps_service.MAX_CPS:
                return SRTCue(index=cue.index, start_ms=cue.start_ms, end_ms=cue.end_ms, text=shortened)
        return SRTCue(index=cue.index, start_ms=cue.start_ms, end_ms=cue.end_ms, text=cue.text)


gemini_service = GeminiService()
