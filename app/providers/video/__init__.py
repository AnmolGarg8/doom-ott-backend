from app.core.config import settings
from app.providers.video.bunny_video import BunnyStreamProvider
from app.providers.video.interface import VideoProvider
from app.providers.video.mock_video import MockVideoProvider


def get_video_provider() -> VideoProvider:
    """Factory function returning VideoProvider implementation based on VIDEO_PROVIDER setting."""
    provider_name = settings.VIDEO_PROVIDER.lower()
    if provider_name == "bunny":
        return BunnyStreamProvider()
    return MockVideoProvider()


__all__ = [
    "VideoProvider",
    "MockVideoProvider",
    "BunnyStreamProvider",
    "get_video_provider",
]
