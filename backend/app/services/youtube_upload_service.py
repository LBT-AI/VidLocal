import os
import logging
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.config import settings
from app.services.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


class YouTubeUploadError(Exception):
    pass


class YouTubeThumbnailError(Exception):
    pass


class YouTubeUploadService(BaseAIService):
    def __init__(self):
        super().__init__(
            service_name="YouTubeUpload",
            timeout=120.0,
            retries=2,
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=60.0,
        )
        self._credentials = None
        self._youtube = None

    def _refresh_credentials(self) -> Credentials:
        refresh_token = settings.YOUTUBE_REFRESH_TOKEN
        if not refresh_token:
            raise YouTubeUploadError("YOUTUBE_REFRESH_TOKEN not configured")
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
        )
        creds.refresh(Request())
        return creds

    def _get_service(self):
        if self._youtube is None or not self._credentials.valid:
            self._credentials = self._refresh_credentials()
            self._youtube = build(
                YOUTUBE_API_SERVICE_NAME,
                YOUTUBE_API_VERSION,
                credentials=self._credentials,
                cache_discovery=False,
            )
        return self._youtube

    CATEGORY_IDS = {
        "Film & Animation": "1",
        "Autos & Vehicles": "2",
        "Music": "10",
        "Pets & Animals": "15",
        "Sports": "17",
        "Travel & Events": "19",
        "Gaming": "20",
        "People & Blogs": "22",
        "Comedy": "23",
        "Entertainment": "24",
        "News & Politics": "25",
        "Howto & Style": "26",
        "Education": "27",
        "Science & Technology": "28",
        "Nonprofits & Activism": "29",
    }

    def _resolve_category_id(self, category: str) -> str:
        if not category:
            return "22"
        return self.CATEGORY_IDS.get(category, "22")

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: list | None = None,
        privacy: str = "private",
        category: str = "",
    ) -> dict:
        youtube = self._get_service()
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": (tags or [])[:500],
                "categoryId": self._resolve_category_id(category),
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(file_path, chunksize=5 * 1024 * 1024, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
        video_id = response["id"]
        return {
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
        }

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> dict:
        youtube = self._get_service()
        if not os.path.exists(thumbnail_path):
            raise YouTubeThumbnailError(f"Thumbnail file not found: {thumbnail_path}")
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        request = youtube.thumbnails().set(videoId=video_id, media_body=media)
        response = request.execute()
        logger.info("Thumbnail set for video %s: %s", video_id, response.get("items", []))
        return response


youtube_upload_service = YouTubeUploadService()
