import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx

from downloaders.base import BaseDownloader


logger = logging.getLogger(__name__)

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)
VIDEO_ID_PATTERNS = [
    re.compile(r"/video/(\d+)"),
    re.compile(r"[?&](?:modal_id|aweme_id|item_ids)=(\d+)"),
]
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov"}


class DouyinDownloadError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.metadata = metadata or {}


class DouyinDownloader(BaseDownloader):
    name = "douyin"
    domains = ["douyin.com", "v.douyin.com"]

    async def preprocess(self, url: str) -> dict:
        return await preprocess_douyin_url(url)

    async def download(
        self,
        data: dict,
        *,
        output_dir: str = "/app/data/downloads",
        cookies_file: str = "",
        proxy: str = "",
        user_agent: str = "",
        timeout_seconds: int = 900,
    ) -> str:
        return await download_douyin_from_preprocessed(
            data,
            output_dir=output_dir,
            cookies_file=cookies_file,
            proxy=proxy,
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
        )


def extract_douyin_video_id(url: str) -> str | None:
    for pattern in VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


async def preprocess_douyin_url(url: str) -> dict[str, str | None]:
    resolved_url = await _resolve_redirect(url)
    video_id = extract_douyin_video_id(resolved_url) or extract_douyin_video_id(url)
    normalized_url = f"https://www.douyin.com/video/{video_id}" if video_id else resolved_url

    metadata = {
        "platform": "douyin",
        "original_url": url,
        "resolved_url": resolved_url,
        "video_id": video_id,
        "normalized_url": normalized_url,
    }
    logger.info(
        "Douyin preprocess original_url=%s resolved_url=%s video_id=%s normalized_url=%s",
        url,
        resolved_url,
        video_id,
        normalized_url,
    )
    return metadata


async def download_douyin(
    url: str,
    *,
    output_dir: str = "/app/data/downloads",
    cookies_file: str = "",
    proxy: str = "",
    user_agent: str = "",
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    metadata = await preprocess_douyin_url(url)
    file_path = await download_douyin_from_preprocessed(
        metadata,
        output_dir=output_dir,
        cookies_file=cookies_file,
        proxy=proxy,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
    )
    return {**metadata, "file_path": file_path}


async def download_douyin_from_preprocessed(
    metadata: dict,
    *,
    output_dir: str = "/app/data/downloads",
    cookies_file: str = "",
    proxy: str = "",
    user_agent: str = "",
    timeout_seconds: int = 900,
) -> str:
    normalized_url = metadata.get("normalized_url")
    if not normalized_url or ("v.douyin.com" in (metadata.get("original_url") or "") and not metadata.get("video_id")):
        raise DouyinDownloadError(
            "Không resolve được link Douyin ngắn",
            error_code="douyin_resolve_failed",
            metadata=metadata,
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _cleanup_partial_files(output_path)

    attempts = [
        ("normal", {}),
        ("mobile_headers", {"mobile_headers": True}),
    ]
    if cookies_file and os.path.exists(cookies_file):
        attempts.append(("cookies", {"mobile_headers": True, "cookies_file": cookies_file}))

    last_error: DouyinDownloadError | None = None
    for attempt_name, options in attempts:
        cmd = _build_command(
            normalized_url,
            output_dir=output_dir,
            proxy=proxy,
            user_agent=user_agent or MOBILE_USER_AGENT,
            **options,
        )
        logger.info("Douyin retry attempt=%s command=%s", attempt_name, _redact_command(cmd))
        try:
            completed = await _run_ytdlp(cmd, timeout_seconds=timeout_seconds)
        except DouyinDownloadError as e:
            last_error = _with_metadata(e, metadata)
            logger.warning("Douyin retry attempt=%s error_code=%s error=%s", attempt_name, e.error_code, e)
            continue

        logger.info("Douyin yt-dlp attempt=%s stdout=%s stderr=%s", attempt_name, completed.stdout, completed.stderr)
        if completed.returncode == 0:
            file_path = _find_downloaded_file(output_path, metadata.get("video_id"))
            if file_path and file_path.stat().st_size > 1024 * 1024:
                return str(file_path)
            last_error = DouyinDownloadError(
                "Douyin download finished but output file is missing or smaller than 1MB",
                error_code="douyin_no_formats",
                metadata=metadata,
            )
            continue

        error_text = (completed.stderr or completed.stdout or "yt-dlp failed").strip()
        last_error = DouyinDownloadError(
            _friendly_error_message(error_text),
            error_code=_map_error_code(error_text),
            metadata=metadata,
        )
        logger.warning(
            "Douyin yt-dlp failed attempt=%s error_code=%s stdout=%s stderr=%s",
            attempt_name,
            last_error.error_code,
            completed.stdout,
            completed.stderr,
        )

    _cleanup_partial_files(output_path)
    raise last_error or DouyinDownloadError(
        "Link Douyin này không tải được.",
        error_code="douyin_no_formats",
        metadata=metadata,
    )


async def _resolve_redirect(url: str) -> str:
    if "v.douyin.com" not in url:
        return url

    def _run() -> str:
        try:
            with httpx.Client(follow_redirects=True, timeout=10) as client:
                response = client.get(url, headers={"User-Agent": MOBILE_USER_AGENT})
                return str(response.url) or url
        except Exception:
            logger.warning("Failed to resolve Douyin short URL: %s", url, exc_info=True)
            return url

    return await asyncio.to_thread(_run)


def _build_command(
    url: str,
    *,
    output_dir: str,
    proxy: str,
    user_agent: str,
    mobile_headers: bool = False,
    cookies_file: str = "",
) -> list[str]:
    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "--socket-timeout",
        "30",
        "--retries",
        "2",
        "--fragment-retries",
        "2",
        "--user-agent",
        user_agent,
        "-o",
        os.path.join(output_dir, "%(id)s.%(ext)s"),
    ]
    if mobile_headers:
        cmd.extend([
            "--add-header",
            "Referer:https://www.douyin.com/",
            "--add-header",
            "Accept-Language:zh-CN,zh;q=0.9,en;q=0.8",
        ])
    if proxy:
        cmd.extend(["--proxy", proxy])
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    cmd.append(url)
    return cmd


async def _run_ytdlp(cmd: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    try:
        return await asyncio.to_thread(
            subprocess.run,
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DouyinDownloadError(
            "Douyin download timeout",
            error_code="douyin_download_timeout",
        ) from exc


def _map_error_code(error_text: str) -> str:
    lower = error_text.lower()
    if "no video formats found" in lower or "requested format is not available" in lower:
        return "douyin_no_formats"
    if "login" in lower or "cookie" in lower or "cookies" in lower:
        return "douyin_cookie_required"
    if "http error 403" in lower or "region" in lower or "not available in your country" in lower:
        return "douyin_region_blocked"
    if "timed out" in lower or "timeout" in lower:
        return "douyin_download_timeout"
    return "douyin_no_formats"


def _friendly_error_message(error_text: str) -> str:
    error_code = _map_error_code(error_text)
    if error_code == "douyin_cookie_required":
        return "Link Douyin này không tải được. Có thể video bị giới hạn hoặc cần cookie. Vui lòng thử link khác hoặc cấu hình cookie."
    if error_code == "douyin_region_blocked":
        return "Link Douyin này không tải được. Có thể video bị giới hạn vùng. Vui lòng thử link khác hoặc cấu hình proxy/cookie."
    if error_code == "douyin_download_timeout":
        return "Douyin download timeout"
    return "Link Douyin này không tải được. Có thể video bị giới hạn hoặc cần cookie. Vui lòng thử link khác hoặc cấu hình cookie."


def _find_downloaded_file(output_dir: Path, video_id: str | None) -> Path | None:
    candidates = [
        path for path in output_dir.glob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and path.stat().st_size > 0
    ]
    if video_id:
        matching = [path for path in candidates if video_id in path.stem]
        if matching:
            return max(matching, key=lambda path: path.stat().st_mtime)
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _cleanup_partial_files(output_dir: Path) -> None:
    for path in output_dir.glob("*"):
        if path.suffix.lower() in {".part", ".tmp", ".ytdl"} or path.name.endswith(".part"):
            path.unlink(missing_ok=True)


def _with_metadata(error: DouyinDownloadError, metadata: dict) -> DouyinDownloadError:
    error.metadata = metadata
    return error


def _redact_command(cmd: list[str]) -> list[str]:
    redacted = list(cmd)
    for index, part in enumerate(redacted[:-1]):
        if part in {"--cookies", "--proxy"}:
            redacted[index + 1] = "[redacted]"
    return redacted
