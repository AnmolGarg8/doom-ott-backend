"""
Video Provider abstraction module (Transcoding / Streaming).
"""
from app.core.config import settings


async def process_video(video_id: str, source_url: str) -> dict:
    """Process video via configured provider (mock or live)."""
    if settings.VIDEO_PROVIDER == "mock":
        print(f"[MOCK VIDEO] Processing video {video_id} from {source_url}")
        return {"status": "queued", "video_id": video_id, "provider": "mock"}
    else:
        raise NotImplementedError(f"Video Provider '{settings.VIDEO_PROVIDER}' not implemented.")
