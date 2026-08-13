from app.core.config import settings
from app.providers.image.bunny_image import BunnyStorageProvider
from app.providers.image.interface import ImageProvider
from app.providers.image.mock_image import MockImageProvider


def get_image_provider() -> ImageProvider:
    """Factory function returning ImageProvider implementation based on IMAGE_PROVIDER setting."""
    provider_name = getattr(settings, "IMAGE_PROVIDER", "mock").lower()
    if provider_name in ("bunny", "bunnystorage"):
        return BunnyStorageProvider()
    return MockImageProvider()


__all__ = [
    "ImageProvider",
    "MockImageProvider",
    "BunnyStorageProvider",
    "get_image_provider",
]
