"""Database session and engine setup."""

from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Azure PostgreSQL requires SSL; asyncpg needs an ssl.SSLContext, not a URL param
_connect_args: dict = {}
if "azure" in settings.database_url:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE
    _connect_args["ssl"] = _ssl_ctx

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with async_session_factory() as session:
        yield session
