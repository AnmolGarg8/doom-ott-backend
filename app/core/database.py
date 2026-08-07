import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

database_url = settings.DATABASE_URL

# Fallback to local SQLite file database if USE_SQLITE environment variable is set or PostgreSQL is unavailable
if os.getenv("USE_SQLITE", "false").lower() == "true":
    database_url = "sqlite+aiosqlite:///./doom_ott_dev.db"

# Engine configuration kwargs
engine_kwargs = {"echo": False, "future": True}
if "postgresql" in database_url:
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base model for all SQLAlchemy database models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator yielding an async database session for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
