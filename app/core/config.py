from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Doom OTT Backend"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    CORS_ALLOWED_ORIGINS: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/doom_ott"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security / JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Provider Mode Flags (mock or live provider name)
    SMS_PROVIDER: str = "mock"
    VIDEO_PROVIDER: str = "mock"
    PAYMENT_PROVIDER: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    def validate_secrets(self) -> None:
        burned_or_placeholder_keys = {
            "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
            "REPLACE_WITH_YOUR_OWN_SECRET_generate_via_openssl_rand_hex_32",
            "change_me",
            "secret",
            "",
        }
        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY in burned_or_placeholder_keys:
            raise ValueError(
                "CRITICAL SECURITY ERROR: JWT_SECRET_KEY is missing, empty, or using a burned/placeholder key. "
                "Please generate a new random 32-byte hex secret (e.g. openssl rand -hex 32) and set it in your local .env file."
            )


settings = Settings()
settings.validate_secrets()
