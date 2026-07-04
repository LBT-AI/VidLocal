import asyncio
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from downloaders.base import BaseDownloader


logger = logging.getLogger(__name__)

BVID_PATTERN = re.compile(r"(BV[0-9A-Za-z]+)")
AID_PATTERNS = [
    re.compile(r"/video/av(\d+)", re.IGNORECASE),
    re.compile(r"[?&]aid=(\d+)", re.IGNORECASE),
]
BROWSER_HEADERS = {
    "Referer": "https://www.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.bilibili.com",
}
SOCKET_TIMEOUT_SECONDS = 30
YTDLP_RETRIES = 2
STRATEGY_RETRIES = 2


@dataclass(frozen=True)
class BilibiliStrategy:
    name: str
    use_headers: bool = False
    cookies_file: str | None = None
    proxy: str | None = None


class BilibiliDownloadError(Exception):
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


class BilibiliDownloader(BaseDownloader):
    name = "bilibili"
    domains = ["bilibili.com", "b23.tv"]

    async def preprocess(self, url: str) -> dict:
        return await preprocess_bilibili_url(url)

    async def download(
        self,
        data: dict,
        *,
        output_dir: str = "/app/data/downloads",
        cookies_file: str | None = None,
        timeout_seconds: int = 900,
    ) -> str:
        return await download_bilibili_from_preprocessed(
            data,
            output_dir=output_dir,
            cookies_file=cookies_file,
            timeout_seconds=timeout_seconds,
        )


def is_bilibili_url(url: str) -> bool:
    return BilibiliDownloader().match(url)


def extract_bilibili_video_id(url: str) -> str | None:
    bvid_match = BVID_PATTERN.search(url)
    if bvid_match:
        return bvid_match.group(1)

    for pattern in AID_PATTERNS:
        aid_match = pattern.search(url)
        if aid_match:
            return f"av{aid_match.group(1)}"

    return None


async def resolve_redirect(url: str) -> str:
    if "b23.tv" not in url:
        return url

    def _run() -> str:
        try:
            with httpx.Client(follow_redirects=True, timeout=10) as client:
                response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                return str(response.url) or url
        except Exception:
            logger.warning("Failed to resolve Bilibili short URL: %s", url, exc_info=True)
            return url

    return await asyncio.to_thread(_run)


async def preprocess_bilibili_url(url: str) -> dict[str, str | None]:
    resolved_url = await resolve_redirect(url)
    video_id = extract_bilibili_video_id(resolved_url) or extract_bilibili_video_id(url)
    normalized_url = _normalize_url(video_id, resolved_url)

    metadata = {
        "platform": "bilibili",
        "original_url": url,
        "resolved_url": resolved_url,
        "video_id": video_id,
        "normalized_url": normalized_url,
    }
    logger.info(
        "Bilibili preprocess original_url=%s resolved_url=%s video_id=%s normalized_url=%s",
        url,
        resolved_url,
        video_id,
        normalized_url,
    )
    return metadata


async def download_bilibili(
    url: str,
    *,
    output_dir: str = "/app/data/downloads",
    cookies_file: str | None = None,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    metadata = await preprocess_bilibili_url(url)
    file_path = await download_bilibili_from_preprocessed(
        metadata,
        output_dir=output_dir,
        cookies_file=cookies_file,
        timeout_seconds=timeout_seconds,
    )
    return {
        **metadata,
        "file_path": file_path,
    }


async def download_bilibili_from_preprocessed(
    metadata: dict,
    *,
    output_dir: str = "/app/data/downloads",
    cookies_file: str | None = None,
    timeout_seconds: int = 900,
) -> str:
    normalized_url = metadata["normalized_url"]
    if not normalized_url:
        raise BilibiliDownloadError(
            "Không tìm thấy video ID từ link Bilibili",
            error_code="bilibili_video_id_not_found",
            metadata=metadata,
        )

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    active_cookies_file = _resolve_cookies_file(cookies_file)
    active_proxy = os.getenv("BILIBILI_PROXY")

    if not active_cookies_file and not active_proxy:
        raise BilibiliDownloadError(
            "Bilibili cần cookie hoặc proxy",
            error_code="cookie_or_proxy_required",
            metadata=metadata,
        )

    attempts: list[dict[str, Any]] = []
    last_error_text = "yt-dlp failed"
    last_error_code = "bilibili_download_failed"
    last_strategy = "unknown"

    for strategy in _build_strategies(active_cookies_file, active_proxy):
        last_strategy = strategy.name
        for retry_index in range(1, STRATEGY_RETRIES + 1):
            cmd = _build_ytdlp_command(normalized_url, output_dir, strategy)
            logger.info(
                "Bilibili yt-dlp attempt original_url=%s resolved_url=%s extracted_bvid=%s "
                "normalized_url=%s selected_downloader=yt-dlp strategy=%s retry=%s/%s "
                "headers_used=%s cookies_used=%s proxy_used=%s command=%s",
                metadata.get("original_url"),
                metadata.get("resolved_url"),
                metadata.get("video_id"),
                normalized_url,
                strategy.name,
                retry_index,
                STRATEGY_RETRIES,
                strategy.use_headers,
                bool(strategy.cookies_file),
                bool(strategy.proxy),
                _redact_command(cmd),
            )

            try:
                completed = await _run_ytdlp(cmd, timeout_seconds=timeout_seconds)
            except BilibiliDownloadError as exc:
                last_error_text = str(exc)
                last_error_code = exc.error_code or "bilibili_download_failed"
                attempts.append(_attempt_log(strategy, retry_index, None, last_error_code, last_error_text))
                logger.warning(
                    "Bilibili yt-dlp failed strategy=%s retry=%s error_code=%s stdout=%s stderr=%s",
                    strategy.name,
                    retry_index,
                    last_error_code,
                    "",
                    _trim_log(last_error_text),
                )
                _cleanup_partial_files(output_dir)
                continue

            stdout = _trim_log(completed.stdout)
            stderr = _trim_log(completed.stderr)
            error_text = (completed.stderr or completed.stdout or "yt-dlp failed").strip()
            logger.info(
                "Bilibili yt-dlp result strategy=%s retry=%s returncode=%s stdout=%s stderr=%s",
                strategy.name,
                retry_index,
                completed.returncode,
                stdout,
                stderr,
            )

            if completed.returncode != 0:
                last_error_text = error_text
                last_error_code = _map_error_code(error_text)
                attempts.append(_attempt_log(strategy, retry_index, completed, last_error_code, error_text))
                logger.warning(
                    "Bilibili yt-dlp failed strategy=%s retry=%s error_code=%s stdout=%s stderr=%s",
                    strategy.name,
                    retry_index,
                    last_error_code,
                    stdout,
                    stderr,
                )
                _cleanup_partial_files(output_dir)
                continue

            file_path = _find_downloaded_file(output_dir, metadata["video_id"])
            file_size = file_path.stat().st_size if file_path else 0
            is_large_enough = file_size > 1024 * 1024
            logger.info(
                "Bilibili yt-dlp file_check strategy=%s retry=%s file_path=%s file_size=%s larger_than_1mb=%s",
                strategy.name,
                retry_index,
                str(file_path) if file_path else None,
                file_size,
                is_large_enough,
            )

            if file_path and is_large_enough:
                try:
                    from app.services.ffmpeg_service import FFmpegService
                    ff_meta = await FFmpegService.get_metadata(str(file_path))
                    if not ff_meta.get("video_codec") or ff_meta.get("duration", 0) <= 0:
                        raise ValueError(f"Invalid video metadata: {ff_meta}")
                    
                    metadata["attempts"] = attempts + [
                        _attempt_log(strategy, retry_index, completed, None, "success")
                    ]
                    return str(file_path)
                except Exception as e:
                    logger.warning("Bilibili downloaded file verification failed: %s", e)
                    last_error_text = f"File verification failed: {e}"
                    last_error_code = "bilibili_verify_failed"
                    attempts.append(_attempt_log(strategy, retry_index, completed, last_error_code, last_error_text))
                    _cleanup_partial_files(output_dir)
                    continue

            last_error_text = "yt-dlp did not produce a Bilibili video file larger than 1MB"
            last_error_code = "bilibili_file_too_small" if file_path else "bilibili_download_missing_file"
            attempts.append(_attempt_log(strategy, retry_index, completed, last_error_code, last_error_text))
            _cleanup_partial_files(output_dir)

    metadata["attempts"] = attempts
    metadata["failed_strategy"] = last_strategy
    logger.warning(
        "Bilibili download final_failure error_code=%s failed_strategy=%s attempts=%s",
        last_error_code,
        last_strategy,
        attempts,
    )
    raise BilibiliDownloadError(
        _friendly_error_message(last_error_text),
        error_code=last_error_code,
        metadata=metadata,
    )


def _normalize_url(video_id: str | None, fallback_url: str) -> str:
    if not video_id:
        return fallback_url
    if video_id.startswith("BV"):
        return f"https://www.bilibili.com/video/{video_id}?p=1"
    return f"https://www.bilibili.com/video/{video_id}?p=1"


def _resolve_cookies_file(cookies_file: str | None) -> str | None:
    candidate = cookies_file or os.getenv("BILIBILI_COOKIES_FILE")
    if candidate and os.path.exists(candidate):
        import shutil
        writable_path = "/tmp/bilibili_cookies_writable.txt"
        try:
            shutil.copy2(candidate, writable_path)
            logger.info("Copied cookies from %s to writable path %s", candidate, writable_path)
            return writable_path
        except Exception:
            logger.warning("Failed to copy cookies to %s, using original path", writable_path, exc_info=True)
            return candidate
    return None


def _build_strategies(cookies_file: str | None, proxy: str | None) -> list[BilibiliStrategy]:
    strategies = []
    if cookies_file:
        strategies.append(
            BilibiliStrategy(name="cookies", use_headers=True, cookies_file=cookies_file)
        )
    if proxy:
        strategies.append(
            BilibiliStrategy(name="proxy", use_headers=True, cookies_file=cookies_file, proxy=proxy)
        )
    strategies.extend([
        BilibiliStrategy(name="normal"),
        BilibiliStrategy(name="browser_headers", use_headers=True),
    ])
    return strategies


def _build_ytdlp_command(url: str, output_dir: str, strategy: BilibiliStrategy) -> list[str]:
    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "--socket-timeout",
        str(SOCKET_TIMEOUT_SECONDS),
        "--retries",
        str(YTDLP_RETRIES),
        "--fragment-retries",
        str(YTDLP_RETRIES),
        "-o",
        os.path.join(output_dir, "%(id)s.%(ext)s"),
    ]
    if strategy.use_headers:
        cmd.extend(
            [
                "--referer",
                BROWSER_HEADERS["Referer"],
                "--user-agent",
                BROWSER_HEADERS["User-Agent"],
                "--add-header",
                f"Accept-Language:{BROWSER_HEADERS['Accept-Language']}",
                "--add-header",
                f"Origin:{BROWSER_HEADERS['Origin']}",
            ]
        )
    if strategy.cookies_file:
        cmd.extend(["--cookies", strategy.cookies_file])
    if strategy.proxy:
        cmd.extend(["--proxy", strategy.proxy])
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
        raise BilibiliDownloadError(
            "Bilibili download timeout",
            error_code="bilibili_download_timeout",
        ) from exc


def _find_downloaded_file(output_dir: str, video_id: str | None) -> Path | None:
    candidates = [
        path for path in Path(output_dir).glob("*")
        if path.is_file() and path.suffix.lower() in {".mp4", ".mkv", ".webm"} and path.stat().st_size > 0
    ]
    if video_id:
        matching = [path for path in candidates if video_id in path.stem]
        if matching:
            return max(matching, key=lambda path: path.stat().st_mtime)
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _cleanup_partial_files(output_dir: str) -> None:
    for pattern in ("*.part", "*.tmp", "*.ytdl"):
        for path in Path(output_dir).glob(pattern):
            try:
                path.unlink()
                logger.info("Bilibili cleanup partial_file=%s", path)
            except OSError:
                logger.warning("Bilibili cleanup failed partial_file=%s", path, exc_info=True)


def _attempt_log(
    strategy: BilibiliStrategy,
    retry_index: int,
    completed: subprocess.CompletedProcess[str] | None,
    error_code: str | None,
    message: str,
) -> dict[str, Any]:
    return {
        "strategy": strategy.name,
        "retry": retry_index,
        "headers_used": strategy.use_headers,
        "cookies_used": bool(strategy.cookies_file),
        "proxy_used": bool(strategy.proxy),
        "returncode": completed.returncode if completed else None,
        "stdout": _trim_log(completed.stdout if completed else ""),
        "stderr": _trim_log(completed.stderr if completed else message),
        "error_code": error_code,
    }


def _trim_log(text: str | None, *, limit: int = 1200) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}... [truncated]"


def _map_error_code(error_text: str) -> str:
    lower_text = error_text.lower()
    if "timed out" in lower_text or "timeout" in lower_text:
        return "bilibili_download_timeout"
    if "http error 412" in lower_text or "412: precondition failed" in lower_text:
        return "region_blocked"
    if "no video formats found" in lower_text:
        return "bilibili_no_formats"
    if "http error 403" in lower_text and (
        "cookie" in lower_text or "login" in lower_text or "sign in" in lower_text
    ):
        return "cookie_required"
    if "this video is for premium" in lower_text or "login" in lower_text or "cookie" in lower_text:
        return "cookie_required"
    if "http error 403" in lower_text or "403: forbidden" in lower_text:
        return "forbidden"
    return "bilibili_download_failed"


def _friendly_error_message(error_text: str) -> str:
    error_code = _map_error_code(error_text)
    if error_code == "region_blocked":
        return "Bilibili chặn vùng truy cập video này"
    if error_code == "cookie_required":
        return "Video Bilibili cần cookie hoặc tài khoản premium"
    if error_code == "bilibili_no_formats":
        return "Không tìm thấy video format từ Bilibili"
    if error_code == "bilibili_download_timeout":
        return "Tải video Bilibili quá thời gian chờ"
    if error_code == "forbidden":
        return "Bilibili từ chối truy cập video này"
    return error_text


def _redact_command(cmd: list[str]) -> list[str]:
    redacted = list(cmd)
    for index, part in enumerate(redacted[:-1]):
        if part == "--cookies":
            redacted[index + 1] = "[cookies-file]"
        if part == "--proxy":
            redacted[index + 1] = "[proxy]"
    return redacted
