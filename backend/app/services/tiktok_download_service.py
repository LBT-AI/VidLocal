import os
import re
import logging
from app.services.base_ai_service import BaseAIService, RetryExhaustedError
from app.services.ytdlp_download import download_with_ytdlp_process, YtDlpTimeoutError

logger = logging.getLogger(__name__)

TIKTOK_PATTERNS = [
    re.compile(r"https?://(?:www\.)?tiktok\.com/@[\w.\-]+/video/\d+"),
    re.compile(r"https?://(?:www\.)?tiktok\.com/@[\w.\-]+/photo/\d+"),
    re.compile(r"https?://vm\.tiktok\.com/[\w\-]+"),
    re.compile(r"https?://m\.tiktok\.com/v/\d+"),
    re.compile(r"https?://(?:www\.)?tiktok\.com/t/\d+"),
]


class TikTokDownloadError(Exception):
    pass


class TikTokDownloadService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="TikTokDownload",
            timeout=300.0,
            retries=2,
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=60.0,
        )

    @staticmethod
    def validate_url(url: str) -> bool:
        return any(p.match(url) for p in TIKTOK_PATTERNS)

    async def download_with_metadata(self, url: str, output_dir: str) -> dict:
        os.makedirs(output_dir, exist_ok=True)
        try:
            return await self.call_with_retry_async(
                self._download_with_ytdlp, url, output_dir
            )
        except RetryExhaustedError as e:
            raise TikTokDownloadError(f"Download failed: {e}") from e
        except YtDlpTimeoutError as e:
            raise TikTokDownloadError(str(e)) from e

    async def _download_with_ytdlp(self, url: str, output_dir: str) -> dict:
        return await download_with_ytdlp_process(url, output_dir)

    async def download(self, url: str, output_dir: str) -> str:
        result = await self.download_with_metadata(url, output_dir)
        return result["title"]


tiktok_download_service = TikTokDownloadService()
