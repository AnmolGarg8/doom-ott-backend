from abc import ABC, abstractmethod


class ImageProvider(ABC):
    """Abstract Base Class for Image Storage/CDN Providers."""

    @abstractmethod
    async def upload_image(self, file_bytes: bytes, filename: str) -> str:
        """Upload image bytes to storage provider and return a public URL."""
        pass
