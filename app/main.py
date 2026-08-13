import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import Base, engine
from app.core.limiter import limiter
from app.routers import auth_router, content_router, payment_router, subscription_router, users_router
from app.routers.admin import billing_admin_router, content_admin_router, user_admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist and static uploads directory exists
    os.makedirs("static/uploads", exist_ok=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[Lifespan Warning] Could not auto-create tables: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# SlowAPI Rate Limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
if settings.CORS_ALLOWED_ORIGINS.strip():
    allowed_origins = [
        origin.strip()
        for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
elif settings.ENVIRONMENT.lower() == "development":
    allowed_origins = ["*"]
else:
    allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for local image uploads
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(content_router)
app.include_router(subscription_router)
app.include_router(payment_router)
app.include_router(content_admin_router)
app.include_router(billing_admin_router)
app.include_router(user_admin_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint returning application status."""
    return {"status": "ok"}
