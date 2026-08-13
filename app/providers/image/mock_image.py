import os
import uuid
from app.providers.image.interface import ImageProvider


class MockImageProvider(ImageProvider):
    """Mock Image Provider saving uploaded images to a local static/uploads/ directory."""

    def __init__(self, upload_dir: str = "static/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def upload_image(self, file_bytes: bytes, filename: str) -> str:
        name_part, ext = os.path.splitext(filename)
        safe_ext = ext.lower() if ext else ".png"
        unique_name = f"{uuid.uuid4().hex[:12]}_{name_part[:20]}{safe_ext}"
        file_path = os.path.join(self.upload_dir, unique_name)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return f"/static/uploads/{unique_name}"
