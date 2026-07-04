import asyncio
import os
import re
import logging
from app.services.base_ai_service import BaseAIService, RetryExhaustedError
from app.config import settings
from app.services.ytdlp_download import (
    YtDlpNoFormatsError,
    YtDlpTimeoutError,
    download_with_ytdlp_process,
    resolve_webpage_url,
)

logger = logging.getLogger(__name__)

FACEBOOK_PATTERNS = [
    re.compile(r"https?://(?:www\.)?facebook\.com/[\w./\-]+/videos/[\w\-]+"),
    re.compile(r"https?://(?:www\.)?facebook\.com/watch/?\?v=\d+"),
    re.compile(r"https?://(?:www\.)?facebook\.com/reel/\d+"),
    re.compile(r"https?://(?:www\.)?facebook\.com/[\w./\-]+\?__cft__"),
    re.compile(r"https?://fb\.watch/[\w\-]+"),
    re.compile(r"https?://m\.facebook\.com/[\w./\-]+"),
    re.compile(r"https?://(?:www\.)?facebook\.com/[\w./\-]+/posts/[\w\-]+"),
    re.compile(r"https?://(?:www\.)?facebook\.com/share/v/[\w\-]+"),
]

VIDEO_ID_PATTERNS = [
    re.compile(r"/videos/(\d+)"),
    re.compile(r"/reel/(\d+)"),
    re.compile(r"[?&]v=(\d+)"),
]


class FacebookDownloadError(Exception):
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        metadata: dict | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.metadata = metadata or {}


def extract_fb_video_id(url: str) -> str | None:
    for pattern in VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


class FacebookDownloadService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="FacebookDownload",
            timeout=300.0,
            retries=2,
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=60.0,
        )

    @staticmethod
    def validate_url(url: str) -> bool:
        return any(p.match(url) for p in FACEBOOK_PATTERNS)

    async def resolve_url(self, url: str) -> str:
        if "/share/" in url or "fb.watch" in url:
            requests_resolved = await self._resolve_redirect_url(url)
            if requests_resolved != url:
                return requests_resolved
        return await resolve_webpage_url(
            url,
            cookies_file=settings.FACEBOOK_COOKIES_FILE,
        )

    async def preprocess_facebook_url(self, url: str) -> dict:
        resolved_url = await self.resolve_url(url)
        video_id = extract_fb_video_id(resolved_url) or extract_fb_video_id(url)
        normalized_url = (
            f"https://www.facebook.com/watch/?v={video_id}"
            if video_id
            else resolved_url
        )
        metadata = {
            "original_url": url,
            "resolved_url": resolved_url,
            "video_id": video_id,
            "normalized_url": normalized_url,
        }
        logger.info(
            "Facebook preprocess original_url=%s resolved_url=%s video_id=%s normalized_url=%s",
            url,
            resolved_url,
            video_id,
            normalized_url,
        )
        return metadata

    async def download_with_metadata(self, url: str, output_dir: str) -> dict:
        os.makedirs(output_dir, exist_ok=True)
        metadata = await self.preprocess_facebook_url(url)
        normalized_url = metadata["normalized_url"]
        try:
            result = await self._download_with_controlled_retries(
                normalized_url,
                output_dir,
                cookies_file="",
            )
        except YtDlpNoFormatsError as e:
            cookies_file = settings.FACEBOOK_COOKIES_FILE
            if cookies_file and os.path.exists(cookies_file):
                try:
                    result = await self._download_with_controlled_retries(
                        normalized_url,
                        output_dir,
                        cookies_file=cookies_file,
                    )
                except YtDlpNoFormatsError as retry_error:
                    raise FacebookDownloadError(
                        "Không tìm thấy video format. Có thể link private hoặc cần cookie.",
                        error_code="facebook_no_formats",
                        metadata=metadata,
                    ) from retry_error
            else:
                error_code = "facebook_no_formats" if metadata["video_id"] else "facebook_video_id_not_found"
                message = (
                    "Không tìm thấy video format. Có thể link private hoặc cần cookie."
                    if metadata["video_id"]
                    else "Không tìm thấy video ID từ link Facebook"
                )
                raise FacebookDownloadError(message, error_code=error_code, metadata=metadata) from e
        except RetryExhaustedError as e:
            raise FacebookDownloadError(f"Download failed: {e}", metadata=metadata) from e
        except YtDlpTimeoutError as e:
            raise FacebookDownloadError(str(e), metadata=metadata) from e

        result.update(metadata)
        return result

    async def _download_with_controlled_retries(
        self,
        url: str,
        output_dir: str,
        *,
        cookies_file: str,
    ) -> dict:
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                return await asyncio.wait_for(
                    self._download_with_ytdlp(url, output_dir, cookies_file=cookies_file),
                    timeout=self.timeout,
                )
            except YtDlpNoFormatsError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(
                    "%s attempt %d/%d failed: %s",
                    self.service_name,
                    attempt + 1,
                    self.retries + 1,
                    e,
                )
                if attempt < self.retries:
                    await asyncio.sleep(1.0 * (attempt + 1))
        raise RetryExhaustedError(f"{self.service_name} failed after {self.retries + 1} attempts: {last_error}")

    async def _download_with_ytdlp(self, url: str, output_dir: str, *, cookies_file: str) -> dict:
        return await download_with_ytdlp_process(
            url,
            output_dir,
            cookies_file=cookies_file,
        )

    async def _resolve_redirect_url(self, url: str) -> str:
        def _run() -> str:
            try:
                import httpx

                response = httpx.get(
                    url,
                    allow_redirects=True,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                return response.url or url
            except Exception:
                return url

        return await asyncio.to_thread(_run)

    async def download(self, url: str, output_dir: str) -> str:
        result = await self.download_with_metadata(url, output_dir)
        return result["title"]


facebook_download_service = FacebookDownloadService()
