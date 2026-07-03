import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from typing import Optional
from pathlib import Path
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from app.config import settings
from app.services.base_ai_service import BaseAIService, RetryExhaustedError

logger = logging.getLogger(__name__)

FRAME_EXTRACT_INTERVAL = 5
MAX_FRAMES = 20
TOP_FRAMES = 6
THUMBNAIL_REFS_DIR = "thumbnail_refs"

FRAME_SCORE_PROMPT = """You are a thumbnail quality evaluator. Analyze the given video frame and score it for use as a YouTube thumbnail reference.

Score each frame (0-10) on these criteria:
1. **face_quality** — Is the character's face clear, visible, well-lit? (0=no face, 10=perfect face)
2. **composition** — Is the framing well-balanced, cinematic? (0=poor, 10=excellent)
3. **expression** — Does the character have an expressive/interesting facial expression? (0=neutral/boring, 10=very expressive)
4. **sharpness** — Is the frame sharp and clear (not blurry/motion-blurred)? (0=very blurry, 10=tack sharp)
5. **thumbnail_potential** — Would this make a good YouTube thumbnail reference? (0=useless, 10=perfect)

Return JSON array:
[
  {"index": 0, "face_quality": 0, "composition": 0, "expression": 0, "sharpness": 0, "thumbnail_potential": 0, "has_face": false, "face_description": "", "scene_description": ""}
]

Only return the JSON, no preamble."""


class ThumbnailReferenceError(Exception):
    pass


class ThumbnailReferenceService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="ThumbnailReference",
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            retries=max(settings.GEMINI_RETRIES, 0),
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=30.0,
        )
        self._vision_model = None
        self._init_vision()

    def _init_vision(self):
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model_name = settings.AI_MODEL or "gemini-1.5-flash-latest"
                self._vision_model = genai.GenerativeModel(model_name)
                logger.info("ThumbnailReference: vision model initialized")
            except Exception as e:
                logger.warning("ThumbnailReference: failed to init vision: %s", e)

    @property
    def vision_available(self) -> bool:
        return self._vision_model is not None

    def _get_video_duration(self, video_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception as e:
            raise ThumbnailReferenceError(f"Failed to get video duration: {e}")

    def extract_frames(self, video_path: str, output_dir: str, interval: int = FRAME_EXTRACT_INTERVAL) -> list:
        """Extract frames every `interval` seconds, return list of frame paths sorted by timestamp."""
        os.makedirs(output_dir, exist_ok=True)
        duration = self._get_video_duration(video_path)
        logger.info("Video duration: %.1fs, extracting frames every %ds", duration, interval)

        pattern = os.path.join(output_dir, "frame_%04d.jpg")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps=1/{interval},scale=640:-1",
            "-q:v", "3",
            "-vsync", "vfr",
            "-frame_pts", "1",
            "-y",
            pattern,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg frame extraction timed out")

        frame_files = sorted(
            [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".jpg")],
            key=lambda x: int(re.search(r"frame_(\d+)", os.path.basename(x)).group(1)),
        )

        if not frame_files:
            raise ThumbnailReferenceError("No frames extracted from video")

        # If too many frames, thin them
        if len(frame_files) > MAX_FRAMES:
            step = len(frame_files) // MAX_FRAMES
            frame_files = frame_files[::step][:MAX_FRAMES]

        logger.info("Extracted %d frames", len(frame_files))
        return frame_files

    def _compute_sharpness(self, frame_path: str) -> float:
        cmd = [
            "ffmpeg", "-i", frame_path,
            "-vf", "laplacian=scale=1:format=gray,noise=alls=20:allf=t+u,metadata=print:file=-",
            "-f", "null", "-",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            # Parse sharpness from metadata (approximate)
            # Use a simpler approach: run laplacian and get mean
            cmd2 = [
                "ffmpeg", "-i", frame_path,
                "-vf", "laplacian,format=gray,smear=0:0,histogram",
                "-f", "null", "-",
            ]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
            # If both fail, estimate from file size vs dimensions
            return 5.0
        except Exception:
            return 5.0

    def _simple_score_frame(self, frame_path: str) -> dict:
        """Score a frame using simple heuristics (no AI)."""
        import subprocess

        try:
            # Get mean luminance to detect black/white frames
            cmd_luma = [
                "ffmpeg", "-i", frame_path,
                "-vf", "signalstats",
                "-f", "null", "-",
            ]
            r = subprocess.run(cmd_luma, capture_output=True, text=True, timeout=10)
            stderr = r.stderr

            # Estimate sharpness via file size ratio
            file_size = os.path.getsize(frame_path)
            width, height = 640, 360

            # Heuristic score
            sharpness_score = min(10, file_size / 5000)
            composition = 6.0
            face_quality = 0.0
            has_face = False
            expression = 5.0
            thumbnail_potential = sharpness_score * 0.5 + composition * 0.3 + 2.0

            return {
                "face_quality": round(face_quality, 1),
                "composition": round(composition, 1),
                "expression": round(expression, 1),
                "sharpness": round(min(10, sharpness_score), 1),
                "thumbnail_potential": round(min(10, thumbnail_potential), 1),
                "has_face": has_face,
                "face_description": "",
                "scene_description": "",
            }
        except Exception:
            return {
                "face_quality": 0, "composition": 5, "expression": 5,
                "sharpness": 5, "thumbnail_potential": 5, "has_face": False,
                "face_description": "", "scene_description": "",
            }

    def _score_with_vision(self, frame_paths: list) -> list:
        """Use Gemini Vision to score frames. Returns list of score dicts matching frame_paths order."""
        if not self.vision_available or not frame_paths:
            return [self._simple_score_frame(p) for p in frame_paths]

        try:
            import PIL.Image
            images = []
            for fp in frame_paths[:8]:  # Max 8 frames for vision
                try:
                    img = PIL.Image.open(fp)
                    images.append(img)
                except Exception:
                    pass

            if not images:
                return [self._simple_score_frame(p) for p in frame_paths]

            prompt_parts = [FRAME_SCORE_PROMPT] + images
            response = self._vision_model.generate_content(
                prompt_parts,
                request_options={"timeout": max(self.timeout, 120.0)},
            )
            raw = response.text.strip()
            json_match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not json_match:
                logger.warning("Vision did not return JSON, using simple scoring")
                return [self._simple_score_frame(p) for p in frame_paths]

            scores = json.loads(json_match.group())
            if not isinstance(scores, list):
                raise ValueError("not a list")

            # Map scores back to frame_paths
            result = []
            scored_indices = {s.get("index", i): s for i, s in enumerate(scores)}
            for i in range(len(frame_paths)):
                if i in scored_indices:
                    result.append(scored_indices[i])
                else:
                    result.append(self._simple_score_frame(frame_paths[i]))
            return result

        except Exception as e:
            logger.warning("Vision scoring failed: %s", e)
            return [self._simple_score_frame(p) for p in frame_paths]

    def select_best_frames(self, video_path: str, job_id, job_dir: str) -> list:
        """
        Full pipeline:
        1. Extract frames from video
        2. Score frames (AI vision if available, else heuristics)
        3. Select top frames
        4. Copy to thumbnail_refs/ directory
        5. Return list of {path, score, description}
        """
        refs_dir = os.path.join(job_dir, THUMBNAIL_REFS_DIR)
        os.makedirs(refs_dir, exist_ok=True)

        # Clean previous refs
        for f in os.listdir(refs_dir):
            if f.endswith(".jpg"):
                os.remove(os.path.join(refs_dir, f))

        # 1. Extract
        raw_dir = os.path.join(job_dir, "thumbnail_raw_frames")
        frame_paths = self.extract_frames(video_path, raw_dir)

        # 2. Score
        scores = self._score_with_vision(frame_paths)

        # 3. Rank
        ranked = sorted(
            zip(frame_paths, scores),
            key=lambda x: x[1].get("thumbnail_potential", 0),
            reverse=True,
        )

        # 4. Save top frames
        import shutil
        selected = []
        for i, (fp, score) in enumerate(ranked[:TOP_FRAMES]):
            dest = os.path.join(refs_dir, f"ref_{i + 1}.jpg")
            shutil.copy2(fp, dest)
            selected.append({
                "path": dest,
                "index": i,
                "score": score,
                "has_face": score.get("has_face", False),
                "face_description": score.get("face_description", ""),
                "scene_description": score.get("scene_description", ""),
                "thumbnail_potential": score.get("thumbnail_potential", 0),
            })
            logger.info("Selected frame %d: potential=%.1f has_face=%s path=%s",
                        i + 1, score.get("thumbnail_potential", 0), score.get("has_face", False), dest)

        return selected

    def describe_reference(self, frame_path: str, transcript: str, title: str) -> str:
        """Use Gemini Vision to describe the reference frame character/scene for prompt context."""
        if not self.vision_available:
            return ""

        try:
            import PIL.Image
            img = PIL.Image.open(frame_path)
            prompt = (
                "Describe this video frame in detail for a thumbnail designer. "
                "Focus on:\n"
                "1. The main character/subject: appearance, expression, clothing, pose\n"
                "2. The scene setting and composition\n"
                "3. Dominant colors and lighting\n"
                "4. Key visual elements that should be preserved in a thumbnail\n\n"
                f"Video context:\nTitle: {title[:200]}\nTranscript excerpt: {transcript[:500]}"
            )
            response = self._vision_model.generate_content(
                [prompt, img],
                request_options={"timeout": self.timeout},
            )
            return response.text.strip()[:1000]
        except Exception as e:
            logger.warning("Failed to describe reference: %s", e)
            return ""


thumbnail_reference_service = ThumbnailReferenceService()
