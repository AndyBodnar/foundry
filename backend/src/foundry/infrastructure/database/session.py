"""Database session management and connection pooling."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from foundry.config import settings

# Global engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Initialize the database connection pool."""
    global _engine, _session_factory

    _engine = create_async_engine(
        settings.async_database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
        echo=settings.database_echo,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def close_db() -> None:
    """Close the database connection pool."""
    global _engine, _session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session from the pool.

    Yields:
        AsyncSession: Database session for use in async context.

    Usage:
        async with get_session() as session:
            # use session
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_health() -> dict:
    """
    Check database health status.

    Returns:
        Dictionary with health status information.
    """
    if _engine is None:
        return {
            "healthy": False,
            "error": "Database not initialized",
        }

    try:
        async with _engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

        return {
            "healthy": True,
            "pool_size": _engine.pool.size() if hasattr(_engine.pool, 'size') else None,
            "pool_checkedin": _engine.pool.checkedin() if hasattr(_engine.pool, 'checkedin') else None,
            "pool_checkedout": _engine.pool.checkedout() if hasattr(_engine.pool, 'checkedout') else None,
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
        }


def get_engine() -> AsyncEngine:
    """Get the database engine instance."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the session factory instance."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory
