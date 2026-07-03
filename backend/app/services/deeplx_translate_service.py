import logging
from typing import List

import httpx

from app.config import settings
from app.services.srt_service import SRTCue
from app.services.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)


class DeepLXTranslateError(Exception):
    pass


class DeepLXTranslateService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="DeepLX",
            timeout=settings.DEEPLX_TIMEOUT_SECONDS,
            retries=max(settings.DEEPLX_RETRIES, 0),
        )
        self.base_url = settings.DEEPLX_BASE_URL.rstrip("/")
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def translate_cues(
        self,
        cues: List[SRTCue],
        source_lang: str = "ZH",
        target_lang: str = "VI",
        glossary_entries: list = None,
    ) -> List[SRTCue]:
        translated = []
        for cue in cues:
            text = await self.call_with_retry_async(
                self._translate_one, cue.text, source_lang, target_lang
            )
            translated.append(
                SRTCue(
                    index=cue.index,
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                    text=text,
                )
            )
        if glossary_entries:
            from app.services.glossary_service import glossary_service
            for cue in translated:
                cue.text = glossary_service.apply_glossary_to_text(cue.text, glossary_entries)
        return translated

    async def _translate_one(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return ""
        payload = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        response = await self._client.post(f"{self.base_url}/translate", json=payload)
        if response.status_code != 200:
            raise DeepLXTranslateError(
                f"DeepLX non-200 status={response.status_code} body={response.text[:300]}"
            )
        data = response.json()
        translated_text = data.get("data")
        if not isinstance(translated_text, str):
            raise DeepLXTranslateError(f"DeepLX response missing string field data: {data}")
        return translated_text.strip()


deeplx_translate_service = DeepLXTranslateService()
