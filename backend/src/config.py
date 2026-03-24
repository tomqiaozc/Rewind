"""Application configuration using pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://rewind:devpassword@localhost:5432/rewind"

    # Auth
    backend_secret: str = "dev-backend-secret-change-in-production"

    # Azure Blob Storage
    azure_storage_connection_string: str = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
        "K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1"
    )
    azure_storage_container_name: str = "sessions"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "https://rewind.dev.example.com"]

    # Security limits
    max_content_size_bytes: int = 52_428_800  # 50MB
    max_decompressed_size_bytes: int = 268_435_456  # 256MB
    max_metadata_size_bytes: int = 2_097_152  # 2MB
    max_batch_size: int = 50

    # Rate limiting
    api_rate_limit: str = "100/minute"  # slowapi format

    # Database pool
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Trusted proxies (for X-Forwarded-For)
    trusted_host: str = ""  # set to production domain in prod

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
