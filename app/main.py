from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist (useful for dev / sqlite fallback / postgres startup)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[Lifespan Warning] Could not auto-create tables: {e}")
    yield
    # Shutdown tasks


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# TODO: Restrict allowed origins in production env (e.g., allow_origins=["https://yourdomain.com"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint returning application status."""
    return {"status": "ok"}
