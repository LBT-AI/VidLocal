from services.download_engine import detect_platform, download_video, get_downloader


async def download(url: str, **kwargs):
    return await download_video(url, **kwargs)


__all__ = ["detect_platform", "download", "download_video", "get_downloader"]
