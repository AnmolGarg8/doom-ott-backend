from abc import ABC, abstractmethod


class VideoProvider(ABC):
    """Abstract Base Class for Video Streaming/Transcoding Providers."""

    @abstractmethod
    async def create_upload(self, title: str) -> dict:
        """Create a new video record with the provider and return provider_video_id and upload_url."""
        pass

    @abstractmethod
    async def get_playback_url(self, provider_video_id: str, expiry_seconds: int = 3600) -> str:
        """Generate a time-limited signed playback URL for the given provider_video_id."""
        pass

    @abstractmethod
    async def get_status(self, provider_video_id: str) -> str:
        """Get the current processing status from provider (uploading|processing|ready|failed)."""
        pass
