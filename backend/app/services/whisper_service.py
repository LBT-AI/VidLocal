import os
import json
from typing import Dict, Any
from app.config import settings
from app.services.srt_service import SRTService, SRTCue
from app.services.base_ai_service import BaseAIService


class GoogleSTTService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="GoogleSTT",
            timeout=120.0,
            retries=2,
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=60.0,
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud.speech_v2 import SpeechClient
            self._client = SpeechClient()
        return self._client

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        from google.cloud.speech_v2.types import cloud_speech

        client = self._get_client()
        request = cloud_speech.BatchRecognizeRequest(
            requests=[
                cloud_speech.BatchRecognizeFileMetadata(
                    config=cloud_speech.RecognitionConfig(
                        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                        language_codes=["zh-CN"],
                        model="latest_long",
                        features=cloud_speech.RecognitionFeatures(enable_word_time_offsets=True),
                    ),
                    uri=f"file://{audio_path}"
                )
            ],
            recognizer=f"projects/{settings.GOOGLE_PROJECT_ID}/locations/global/recognizers/_",
            output_config=cloud_speech.RecognitionOutputConfig(
                inline_response_config=cloud_speech.InlineOutputConfig()
            ),
        )
        return self.call_with_retry(client.batch_recognize, request=request)


class WhisperService:
    def __init__(self):
        self.provider = settings.STT_PROVIDER
        self._whisper_model = None
        self._google_stt = GoogleSTTService()

    def _get_whisper_model(self):
        if self._whisper_model is None:
            from faster_whisper import WhisperModel
            self._whisper_model = WhisperModel(
                settings.MODEL_NAME,
                device="cpu",
                compute_type="int8",
            )
        return self._whisper_model

    def transcribe(self, audio_path: str, project_id: str) -> Dict[str, Any]:
        if self.provider == "faster-whisper":
            return self._transcribe_local(audio_path, project_id)
        elif self.provider == "google":
            return self._transcribe_google(audio_path)
        else:
            raise ValueError(f"Unknown STT provider: {self.provider}")

    def _transcribe_local(self, audio_path: str, project_id: str) -> Dict[str, Any]:
        model = self._get_whisper_model()
        segments, info = model.transcribe(audio_path, language="zh", word_timestamps=True, vad_filter=True)
        cues = []
        word_timestamps = []
        for i, segment in enumerate(segments, start=1):
            start_ms = int(segment.start * 1000)
            end_ms = int(segment.end * 1000)
            cues.append(SRTCue(index=i, start_ms=start_ms, end_ms=end_ms, text=segment.text.strip()))
            if segment.words:
                for word in segment.words:
                    word_timestamps.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    })
        srt_content = SRTService.generate(cues)
        return {
            "srt": srt_content,
            "word_timestamps": word_timestamps,
            "language": info.language,
            "language_probability": info.language_probability,
            "cues": cues
        }

    def _transcribe_google(self, audio_path: str) -> Dict[str, Any]:
        response = self._google_stt.transcribe(audio_path)
        cues = []
        word_timestamps = []
        cue_idx = 1
        for result in response.results:
            for transcript in result.transcript_results:
                for alt in transcript.alternatives:
                    start_ms = int(alt.words[0].start_offset.total_seconds() * 1000) if alt.words else 0
                    end_ms = int(alt.words[-1].end_offset.total_seconds() * 1000) if alt.words else 0
                    cues.append(SRTCue(index=cue_idx, start_ms=start_ms, end_ms=end_ms, text=alt.transcript.strip()))
                    cue_idx += 1
                    for word in alt.words:
                        word_timestamps.append({
                            "word": word.word,
                            "start": word.start_offset.total_seconds(),
                            "end": word.end_offset.total_seconds()
                        })
        srt_content = SRTService.generate(cues)
        return {"srt": srt_content, "word_timestamps": word_timestamps, "cues": cues}


whisper_service = WhisperService()
