"""
Database connection and session management.

Uses SQLAlchemy 2.x async engine with asyncpg.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _create_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine from application settings."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.is_development,   # SQL logging in dev only
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,             # Reconnect on stale connections
        pool_recycle=3600,              # Recycle connections every hour
    )


# Lazy singletons — initialised on first use via get_engine() / get_session_factory()
# This allows tests to override the engine before the app starts.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the application-wide async engine, creating it if necessary."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating it if necessary."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


# Convenience aliases kept for backward compatibility with existing imports.
@property  # type: ignore[misc]
def engine() -> AsyncEngine:  # type: ignore[misc]
    return get_engine()


@property  # type: ignore[misc]
def async_session_factory() -> async_sessionmaker[AsyncSession]:  # type: ignore[misc]
    return get_session_factory()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a database session.

    Commits on clean exit, rolls back on exception.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(...)
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Verify the database connection on startup.

    Does NOT create tables — use Alembic migrations instead.
    """
    from sqlalchemy import text

    try:
        async with get_engine().begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_verified")
    except Exception as exc:
        logger.error("database_connection_failed", error=str(exc))
        raise
