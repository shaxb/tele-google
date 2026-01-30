"""
Database Connection Management
Handles async SQLAlchemy engine and session pooling
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from src.config import get_config
from src.utils.logger import get_logger
from src.database.models import Base

log = get_logger(__name__)

# Global engine and session factory
_engine = None
_async_session_factory = None


def get_database_url() -> str:
    """
    Construct async PostgreSQL database URL
    
    Returns:
        Database URL in asyncpg format
    """
    config = get_config()
    db = config.database
    
    return f"postgresql+asyncpg://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"


async def init_db() -> None:
    """
    Initialize database engine and create tables
    Call this once at application startup
    """
    global _engine, _async_session_factory
    
    if _engine is not None:
        log.warning("Database already initialized")
        return
    
    database_url = get_database_url()
    log.info(f"Initializing database connection: {database_url.split('@')[1]}")  # Hide credentials
    
    # Create async engine with connection pooling
    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        pool_size=10,  # Maximum connections in pool
        max_overflow=20,  # Additional connections if pool is full
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )
    
    # Create session factory
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit
        autoflush=False,  # Manual control over flushes
        autocommit=False
    )
    
    # Create all tables (in production, use Alembic migrations instead)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    log.info("Database initialized successfully")


async def close_db() -> None:
    """
    Close database connections
    Call this at application shutdown
    """
    global _engine, _async_session_factory
    
    if _engine is None:
        log.warning("Database not initialized")
        return
    
    log.info("Closing database connections")
    await _engine.dispose()
    _engine = None
    _async_session_factory = None
    log.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session (async context manager)
    
    Usage:
        async with get_db() as db:
            result = await db.execute(select(TelegramSession))
            sessions = result.scalars().all()
    
    Yields:
        AsyncSession: Database session
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_session() -> AsyncSession:
    """
    Get a new database session (for direct use)
    Remember to close the session after use!
    
    Returns:
        AsyncSession: Database session
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    return _async_session_factory()
