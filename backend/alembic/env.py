"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.models.base import Base

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url from environment if available
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    import ssl as ssl_mod

    db_url_val = config.get_main_option("sqlalchemy.url", "")
    connect_args: dict = {}
    if "azure" in db_url_val:
        ssl_ctx = ssl_mod.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_mod.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
