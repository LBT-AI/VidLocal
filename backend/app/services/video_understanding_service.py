import os
import logging
from typing import Optional
from app.config import settings
from app.services.ffmpeg_service import ffmpeg_service, FFmpegError
from app.services.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)


class VideoUnderstandingError(Exception):
    pass


class VideoUnderstandingService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="VideoUnderstanding",
            timeout=600.0,
            retries=1,
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=60.0,
        )
        self._whisper_model = None

    def _get_whisper_model(self):
        if self._whisper_model is None:
            from faster_whisper import WhisperModel
            self._whisper_model = WhisperModel(
                settings.WHISPER_MODEL_NAME,
                device="cpu",
                compute_type="int8",
            )
        return self._whisper_model

    async def extract_audio(self, video_path: str, audio_path: str) -> str:
        try:
            return await ffmpeg_service.extract_audio(video_path, audio_path)
        except FFmpegError as e:
            raise VideoUnderstandingError(f"Audio extraction failed: {e}") from e

    def transcribe(self, audio_path: str) -> dict:
        model = self._get_whisper_model()
        segments, info = model.transcribe(audio_path, word_timestamps=False, vad_filter=True)
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        transcript = " ".join(text_parts)
        language = info.language
        log_transcript = transcript[:200].replace("\n", " ") + ("..." if len(transcript) > 200 else "")
        logger.info("Transcript (%s): %s", language, log_transcript)
        return {
            "transcript": transcript,
            "language": language,
            "language_probability": info.language_probability,
        }

    async def understand(self, video_path: str, job_dir: str) -> dict:
        audio_path = os.path.join(job_dir, "audio.wav")
        await self.extract_audio(video_path, audio_path)
        if not os.path.exists(audio_path):
            raise VideoUnderstandingError(f"Audio file not found at {audio_path}")
        result = await self.call_with_retry_async(
            self.transcribe, audio_path
        )
        try:
            os.remove(audio_path)
        except OSError:
            pass
        return result


video_understanding_service = VideoUnderstandingService()
