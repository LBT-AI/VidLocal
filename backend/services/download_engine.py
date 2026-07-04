import inspect
import logging
from typing import Any

from downloaders import DOWNLOADERS


logger = logging.getLogger(__name__)


def get_downloader(url: str):
    for downloader in DOWNLOADERS:
        if downloader.match(url):
            logger.info(
                "Selected downloader=%s platform=%s url=%s",
                downloader.__class__.__name__,
                downloader.name,
                url,
            )
            return downloader
    raise ValueError("No downloader found")


def detect_platform(url: str):
    return get_downloader(url).name


async def download_video(url: str, **kwargs) -> dict[str, Any]:
    downloader = get_downloader(url)
    data = await _maybe_await(downloader.preprocess(url))
    logger.info("Downloader platform=%s preprocess=%s", downloader.name, data)
    file_path = await _maybe_await(downloader.download(data, **kwargs))
    return {
        "platform": downloader.name,
        "file_path": file_path,
        "meta": data,
    }


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value
