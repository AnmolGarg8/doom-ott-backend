import os
import uuid
import httpx
from app.core.config import settings
from app.providers.image.interface import ImageProvider


class BunnyStorageProvider(ImageProvider):
    """Bunny Storage Zone Provider for storing images and serving via Bunny CDN."""

    def __init__(self):
        self.storage_zone = getattr(settings, "BUNNY_STORAGE_ZONE", "doom-ott-zone")
        self.api_key = getattr(settings, "BUNNY_STORAGE_API_KEY", "")
        self.cdn_url = getattr(settings, "BUNNY_CDN_URL", "https://doom-ott.b-cdn.net")

    async def upload_image(self, file_bytes: bytes, filename: str) -> str:
        if not self.api_key or self.api_key == "REPLACE_WITH_YOUR_BUNNY_STORAGE_API_KEY":
            name_part, ext = os.path.splitext(filename)
            safe_ext = ext.lower() if ext else ".png"
            unique_name = f"mock_{uuid.uuid4().hex[:12]}{safe_ext}"
            return f"{self.cdn_url.rstrip('/')}/{unique_name}"

        name_part, ext = os.path.splitext(filename)
        safe_ext = ext.lower() if ext else ".png"
        unique_name = f"posters/{uuid.uuid4().hex[:16]}{safe_ext}"

        upload_url = f"https://storage.bunnycdn.com/{self.storage_zone}/{unique_name}"
        headers = {
            "AccessKey": self.api_key,
            "Content-Type": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(upload_url, content=file_bytes, headers=headers)
            if response.status_code not in (200, 201):
                raise RuntimeError(f"Bunny Storage API upload failed: {response.status_code} - {response.text}")

        return f"{self.cdn_url.rstrip('/')}/{unique_name}"
