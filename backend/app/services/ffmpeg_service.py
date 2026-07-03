import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings


class FFmpegError(Exception):
    pass


class FFmpegService:
    @staticmethod
    async def run_async(args: list[str], timeout: int = 600, **kwargs) -> str:
        cmd = ["ffmpeg", "-y"] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise FFmpegError(f"FFmpeg timed out after {timeout}s")
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:] if stderr else "Unknown FFmpeg error"
            raise FFmpegError(f"FFmpeg failed: {error_msg}")
        return stdout.decode("utf-8") if stdout else ""

    @staticmethod
    async def extract_audio(video_path: str, output_path: str) -> str:
        args = ["-i", video_path, "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", output_path]
        await FFmpegService.run_async(args)
        return output_path

    @staticmethod
    async def get_metadata(video_path: str) -> Dict[str, Any]:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise FFmpegError("ffprobe timed out")
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:] if stderr else "Unknown ffprobe error"
            raise FFmpegError(f"ffprobe failed: {error_msg}")
        try:
            data = json.loads(stdout.decode("utf-8"))
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
            duration = float(format_info.get("duration", 0))
            fps_str = video_stream.get("r_frame_rate", "0/1")
            fps = eval(fps_str) if "/" in fps_str else float(fps_str)
            return {
                "duration": round(duration, 2),
                "fps": round(fps, 2),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "file_size": int(format_info.get("size", 0)),
                "video_codec": video_stream.get("codec_name"),
                "audio_codec": audio_stream.get("codec_name"),
                "bitrate": int(format_info.get("bit_rate", 0)),
            }
        except Exception as e:
            raise FFmpegError(f"Failed to extract metadata: {str(e)}")

    @staticmethod
    async def render_hardsub(video_path: str, audio_path: str, srt_path: str, output_path: str, style: Optional[str] = None) -> str:
        default_style = "Fontname=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2"
        style_str = style or default_style
        vf = f"subtitles={srt_path}:force_style='{style_str}'"
        args = [
            "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-vf", vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path
        ]
        await FFmpegService.run_async(args)
        return output_path

    @staticmethod
    async def render_softsub(video_path: str, audio_path: str, srt_path: str, output_path: str) -> str:
        args = [
            "-i", video_path, "-i", audio_path, "-i", srt_path,
            "-map", "0:v", "-map", "1:a", "-map", "2",
            "-c:v", "copy", "-c:a", "aac", "-c:s", "mov_text",
            "-metadata:s:s:0", "language=vie",
            "-shortest", output_path
        ]
        await FFmpegService.run_async(args)
        return output_path

    @staticmethod
    async def render_voice_only(video_path: str, audio_path: str, output_path: str) -> str:
        args = [
            "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac",
            "-shortest", output_path
        ]
        await FFmpegService.run_async(args)
        return output_path

    @staticmethod
    async def mix_tts_segments(segments: list[dict], output_path: str, total_duration_ms: int) -> str:
        if not segments:
            raise FFmpegError("No TTS segments to mix")
        inputs = []
        filters = []
        total_sec = total_duration_ms / 1000
        for i, seg in enumerate(segments):
            inputs.extend(["-i", seg["path"]])
            start_sec = seg["start_ms"] / 1000
            filters.append(f"[{i+1}:a]adelay={int(start_sec*1000)}|{int(start_sec*1000)}[a{i}]")
        mix_expr = "[0:a]" + "".join(f"[a{i}]" for i in range(len(segments)))
        filters.append(f"{mix_expr}amix=inputs={len(segments) + 1}:duration=first[aout]")
        filter_complex = ";".join(filters)
        args = (
            ["-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono", "-t", str(total_sec)]
            + inputs
            + ["-filter_complex", filter_complex, "-map", "[aout]", "-c:a", "pcm_s16le", "-ar", "24000", output_path]
        )
        await FFmpegService.run_async(args, timeout=600)
        return output_path

    @staticmethod
    async def normalize_for_youtube(input_path: str, output_path: str, max_height: int = 1080) -> str:
        args = [
            "-i", input_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-vf", "scale='min(1920,iw)':min(1080,ih):force_original_aspect_ratio=decrease",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        await FFmpegService.run_async(args, timeout=600)
        return output_path


ffmpeg_service = FFmpegService()
