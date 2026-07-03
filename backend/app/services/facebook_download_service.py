import asyncio
import os
import re
import logging
from pathlib import Path
from typing import Optional
from app.config import settings
from app.services.base_ai_service import BaseAIService, RetryExhaustedError

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


class FacebookDownloadError(Exception):
    pass


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

    async def download_with_metadata(self, url: str, output_dir: str) -> dict:
        output_path = os.path.join(output_dir, "source.mp4")
        os.makedirs(output_dir, exist_ok=True)
        try:
            return await self.call_with_retry_async(
                self._download_with_ytdlp, url, output_path
            )
        except RetryExhaustedError as e:
            raise FacebookDownloadError(f"Download failed: {e}") from e

    async def _download_with_ytdlp(self, url: str, output_path: str) -> dict:
        import yt_dlp
        loop = asyncio.get_event_loop()
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_path,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
        }
        def _run():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    "title": info.get("title", "Untitled"),
                    "description": info.get("description") or "",
                    "uploader": info.get("uploader") or "",
                    "duration": info.get("duration"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "comment_count": info.get("comment_count"),
                    "thumbnail": info.get("thumbnail") or "",
                    "original_url": info.get("original_url") or "",
                    "webpage_url": info.get("webpage_url") or "",
                }
        result = await loop.run_in_executor(None, _run)
        if not os.path.exists(output_path):
            raise FacebookDownloadError(f"yt-dlp did not produce file at {output_path}")
        return result

    async def download(self, url: str, output_dir: str) -> str:
        result = await self.download_with_metadata(url, output_dir)
        return result["title"]


facebook_download_service = FacebookDownloadService()
