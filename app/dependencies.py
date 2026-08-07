"""
Common FastAPI dependencies re-exports and reusable injection helpers.
"""
from app.core.database import get_db
from app.core.redis_client import get_redis

__all__ = ["get_db", "get_redis"]
