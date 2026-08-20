"""
Shared pytest fixtures for integration tests.

Uses SQLite (via aiosqlite) as an in-memory database so tests can run
without a real PostgreSQL instance.

The environment variables for BOT_TOKEN and DATABASE_URL are patched
here so that importing app.config never raises a validation error
during testing.
"""
import os

# Patch env vars BEFORE any app modules are imported.
# This prevents pydantic-settings from raising ValidationError
# when BOT_TOKEN / DATABASE_URL are missing.
os.environ.setdefault("BOT_TOKEN", "test_bot_token_123:ABC")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_TELEGRAM_IDS", "")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.connection import Base


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create an in-memory SQLite engine for each test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Yield a fresh database session for each test."""
    factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()
