import hashlib
import time
import logging
import httpx
from typing import Optional
from app.core.config import settings
from app.providers.video.interface import VideoProvider

logger = logging.getLogger("doom_ott.video.bunny")


class BunnyStreamProvider(VideoProvider):
    """Bunny Stream Video Provider implementation."""

    def __init__(
        self,
        library_id: str = "",
        api_key: str = "",
        token_key: str = "",
        cdn_hostname: str = "",
    ):
        self.library_id = library_id or getattr(settings, "BUNNY_LIBRARY_ID", "")
        self.api_key = api_key or getattr(settings, "BUNNY_API_KEY", "")
        self.token_key = token_key or getattr(settings, "BUNNY_TOKEN_KEY", "")
        self.cdn_hostname = cdn_hostname or getattr(settings, "BUNNY_CDN_HOSTNAME", "video.doomott.com")

    async def create_upload(self, title: str) -> dict:
        url = f"https://video.bunnycdn.com/library/{self.library_id}/videos"
        headers = {
            "AccessKey": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"title": title}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            video_guid = data.get("guid")

        upload_url = f"https://video.bunnycdn.com/library/{self.library_id}/videos/{video_guid}"
        return {
            "provider_video_id": video_guid,
            "upload_url": upload_url,
        }

    async def get_playback_url(self, provider_video_id: str, expiry_seconds: int = 3600) -> str:
        expires = int(time.time()) + expiry_seconds
        # Bunny Stream Token Signing scheme: SHA256(token_key + video_id + expires)
        hashable = f"{self.token_key}{provider_video_id}{expires}".encode("utf-8")
        token_hash = hashlib.sha256(hashable).hexdigest()

        return f"https://{self.cdn_hostname}/{provider_video_id}/playlist.m3u8?token={token_hash}&expires={expires}"

    async def get_status(self, provider_video_id: str) -> str:
        url = f"https://video.bunnycdn.com/library/{self.library_id}/videos/{provider_video_id}"
        headers = {
            "AccessKey": self.api_key,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return "failed"
            data = response.json()
            status_code = data.get("status")

            # Map Bunny status codes: 0=Created, 1=Uploaded, 2=Processing, 3=Transcoding, 4=Finished, 5=Error
            if status_code in (0, 1):
                return "uploading"
            elif status_code in (2, 3):
                return "processing"
            elif status_code == 4:
                return "ready"
            else:
                return "failed"
