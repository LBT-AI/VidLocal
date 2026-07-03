import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://vidlocal:vidlocal123@localhost:5432/vidlocal"
    REDIS_URL: str = "redis://localhost:6379/0"

    STORAGE_PROVIDER: str = "local"
    S3_BUCKET: str = "vidlocal"
    S3_ENDPOINT: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    PROJECT_DATA_DIR: str = "/app/data/projects"
    MAX_UPLOAD_SIZE: int = 2 * 1024 * 1024 * 1024

    STT_PROVIDER: str = "faster-whisper"
    MODEL_NAME: str = "large-v3"
    WHISPER_MODEL_NAME: str = "base"
    AI_PROVIDER: str = "gemini"
    AI_MODEL: str = ""
    GOOGLE_PROJECT_ID: str = ""
    TRANSLATE_PROVIDER: str = "deeplx"
    DEEPLX_BASE_URL: str = "http://deeplx:1188"
    DEEPLX_TIMEOUT_SECONDS: float = 20.0
    DEEPLX_RETRIES: int = 2
    GEMINI_API_KEY: str = ""
    GEMINI_TIMEOUT_SECONDS: float = 60.0
    GEMINI_RETRIES: int = 2
    DEEPL_API_KEY: str = ""
    TTS_PROVIDER: str = "edge-tts"
    TTS_VOICE: str = "vi-VN-HoaiMyNeural"
    TTS_RATE: str = "+0%"
    TTS_VOLUME: str = "+0%"
    TTS_TIMEOUT_SECONDS: float = 60.0
    TTS_RETRIES: int = 2
    ELEVENLABS_API_KEY: str = ""
    SUBTITLE_OUTPUT_MODE: str = "translated"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002"

    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/connect/youtube/callback"
    YOUTUBE_REFRESH_TOKEN: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""

    MINI_APP_URL: str = "https://telegram-mini-green.vercel.app"

    GLOSSARY_ENABLED: bool = True
    THUMBNAIL_ENABLED: bool = True
    THUMBNAIL_FRAME_INTERVAL: int = 5
    R2_ENABLED: bool = False
    R2_BUCKET: str = ""
    R2_ENDPOINT: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_REGION: str = "auto"
    R2_RETENTION_DAYS: int = 3

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
