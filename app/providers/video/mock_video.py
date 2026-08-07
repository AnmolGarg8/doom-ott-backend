import uuid
from app.providers.video.interface import VideoProvider

# Public test video URLs (matching sample MP4s used in Flutter player test screen)
MOCK_PLAYBACK_URLS = [
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
]


class MockVideoProvider(VideoProvider):
    """Mock Video Provider for local development & testing without real CDN account."""

    async def create_upload(self, title: str) -> dict:
        mock_id = f"mock_vid_{uuid.uuid4().hex[:12]}"
        mock_upload_url = f"http://localhost:8000/admin/dev/mock-upload/{mock_id}"
        return {
            "provider_video_id": mock_id,
            "upload_url": mock_upload_url,
        }

    async def get_playback_url(self, provider_video_id: str, expiry_seconds: int = 3600) -> str:
        # Deterministically select one of the working public test MP4 URLs based on provider_video_id hash
        idx = hash(provider_video_id) % len(MOCK_PLAYBACK_URLS)
        return MOCK_PLAYBACK_URLS[idx]

    async def get_status(self, provider_video_id: str) -> str:
        return "ready"
