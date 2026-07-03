import os
import pickle
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeService:
    @staticmethod
    def _get_redirect_uri() -> str:
        return settings.YOUTUBE_REDIRECT_URI

    @staticmethod
    def get_auth_url(state: str) -> str:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.YOUTUBE_CLIENT_ID,
                    "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [YouTubeService._get_redirect_uri()],
                }
            },
            scopes=SCOPES,
            state=state,
        )
        flow.redirect_uri = YouTubeService._get_redirect_uri()
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
        return auth_url

    @staticmethod
    def exchange_code(code: str) -> dict:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.YOUTUBE_CLIENT_ID,
                    "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [YouTubeService._get_redirect_uri()],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = YouTubeService._get_redirect_uri()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
        }

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict | None:
        if not refresh_token:
            return None
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
        )
        try:
            credentials.refresh(Request())
            return {
                "access_token": credentials.token,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            }
        except Exception:
            return None

    @staticmethod
    def get_valid_credentials(access_token: str, refresh_token: str | None, expires_at: str | None) -> Credentials:
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
        )
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    if refresh_token:
                        refreshed = YouTubeService.refresh_access_token(refresh_token)
                        if refreshed:
                            credentials.token = refreshed["access_token"]
                            if refreshed.get("expires_at"):
                                credentials.expiry = datetime.fromisoformat(refreshed["expires_at"].replace("Z", "+00:00"))
            except Exception:
                pass
        return credentials

    @staticmethod
    def upload_video(access_token: str, file_path: str, title: str, description: str, tags: list, privacy: str,
                     refresh_token: str | None = None, expires_at: str | None = None) -> str:
        credentials = YouTubeService.get_valid_credentials(access_token, refresh_token, expires_at)
        youtube = build("youtube", "v3", credentials=credentials)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            }
        }
        media = MediaFileUpload(file_path, chunksize=5*1024*1024, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
        return f"https://youtube.com/watch?v={response['id']}"


youtube_service = YouTubeService()
