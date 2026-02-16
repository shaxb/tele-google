"""Async database connection management with SQLAlchemy."""

from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.config import get_config

_engine = None
_async_session_factory = None


def get_database_url() -> str:
    db = get_config().database
    return f"postgresql+asyncpg://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"


async def init_db() -> None:
    """Initialize engine, session factory, and create tables. Call once at startup."""
    global _engine, _async_session_factory

    if _engine is not None:
        return

    database_url = get_database_url()
    logger.info(f"Connecting to database: {database_url.split('@')[1]}")

    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    _async_session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Database initialized")


async def close_db() -> None:
    global _engine, _async_session_factory
    if _engine is None:
        return
    await _engine.dispose()
    _engine = None
    _async_session_factory = None
    logger.info("Database connections closed")


def get_session() -> AsyncSession:
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory()
