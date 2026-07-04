import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv", ".mov")


class YtDlpTimeoutError(TimeoutError):
    pass


class YtDlpNoFormatsError(RuntimeError):
    pass


def cleanup_partial_files(output_dir: str) -> None:
    for path in Path(output_dir).glob("source*"):
        if path.suffix in (".part", ".ytdl", ".tmp") or path.name.endswith(".part"):
            path.unlink(missing_ok=True)


async def download_with_ytdlp_process(
    url: str,
    output_dir: str,
    *,
    timeout_seconds: int = 900,
    socket_timeout_seconds: int = 30,
    retries: int = 2,
    cookies_file: str = "",
    format_selector: str = "bv*+ba/best",
) -> dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    cleanup_partial_files(output_dir)

    output_template = os.path.join(output_dir, "source.%(ext)s")
    cmd = [
        "python",
        "-m",
        "yt_dlp",
        "--format",
        format_selector,
        "--output",
        output_template,
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--write-info-json",
        "--socket-timeout",
        str(socket_timeout_seconds),
        "--retries",
        str(retries),
        "--fragment-retries",
        str(retries),
        url,
    ]
    _add_cookies_arg(cmd, cookies_file)

    try:
        completed = await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=output_dir,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        cleanup_partial_files(output_dir)
        raise YtDlpTimeoutError("Download timeout") from exc

    if completed.returncode != 0:
        cleanup_partial_files(output_dir)
        error = (completed.stderr or completed.stdout or "yt-dlp failed").strip()
        if "No video formats found" in error:
            raise YtDlpNoFormatsError(error)
        raise RuntimeError(error)

    video_path = _find_downloaded_video(output_dir)
    if not video_path:
        raise RuntimeError(f"yt-dlp did not produce a video file in {output_dir}")

    info = _read_info_json(output_dir)
    info["filepath"] = str(video_path)
    return info


async def resolve_webpage_url(
    url: str,
    *,
    timeout_seconds: int = 60,
    socket_timeout_seconds: int = 30,
    cookies_file: str = "",
) -> str:
    cmd = [
        "python",
        "-m",
        "yt_dlp",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--print",
        "webpage_url",
        "--socket-timeout",
        str(socket_timeout_seconds),
        url,
    ]
    _add_cookies_arg(cmd, cookies_file)

    try:
        completed = await asyncio.to_thread(
            subprocess.run,
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return url

    resolved_url = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    return resolved_url or url


def _add_cookies_arg(cmd: list[str], cookies_file: str) -> None:
    if cookies_file and os.path.exists(cookies_file):
        cmd[-1:-1] = ["--cookies", cookies_file]


def _find_downloaded_video(output_dir: str) -> Path | None:
    candidates = [
        path for path in Path(output_dir).glob("source.*")
        if path.suffix.lower() in VIDEO_EXTENSIONS and path.stat().st_size > 0
    ]
    return max(candidates, key=lambda path: path.stat().st_size) if candidates else None


def _read_info_json(output_dir: str) -> dict[str, Any]:
    info_files = sorted(Path(output_dir).glob("source*.info.json"))
    if not info_files:
        return {"title": "Untitled"}

    with info_files[-1].open("r", encoding="utf-8") as f:
        info = json.load(f)

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
