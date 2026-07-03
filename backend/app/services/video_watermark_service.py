import os
import logging
from typing import Optional
from app.services.ffmpeg_service import ffmpeg_service, FFmpegError

logger = logging.getLogger(__name__)


class WatermarkError(Exception):
    pass


class VideoWatermarkService:
    async def add_watermark(
        self,
        input_path: str,
        output_path: str,
        watermark_text: str = "@VidLocal",
        position: str = "bottom_right",
    ) -> str:
        if not os.path.exists(input_path):
            raise WatermarkError(f"Input file not found: {input_path}")

        positions = {
            "top_left": "(10,10)",
            "top_right": "(w-tw-10,10)",
            "bottom_left": "(10,h-th-10)",
            "bottom_right": "(w-tw-10,h-th-10)",
        }
        pos = positions.get(position, positions["bottom_right"])

        try:
            args = [
                "-i", input_path,
                "-vf", f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white@0.5:x={pos}:y={pos}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                output_path,
            ]
            await ffmpeg_service.run_async(args, timeout=600)
            logger.info("Watermark added: %s -> %s", input_path, output_path)
            return output_path
        except FFmpegError as e:
            raise WatermarkError(f"Failed to add watermark: {e}") from e


video_watermark = VideoWatermarkService()
