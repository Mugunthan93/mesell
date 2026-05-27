"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://meesell:password@postgres:5432/meesell"

    # Valkey (Redis-compatible)
    VALKEY_URL: str = "redis://valkey:6379/0"
    CELERY_BROKER_URL: str = "redis://valkey:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://valkey:6379/2"

    # AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Storage
    GCS_BUCKET: str = "meesell-dev"
    GCS_PROJECT_ID: str = ""

    # Auth
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    JWT_SECRET: str = "change-this"
    JWT_EXPIRY_DAYS: int = 7

    # Payments
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
