# Database Connection Management
# Handles async SQLAlchemy engine and session pooling

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


# Construct async PostgreSQL database URL
def get_database_url() -> str:
    config = get_config()
    db = config.database
    return f"postgresql+asyncpg://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"


# Initialize database engine and create tables
# Call this once at application startup
async def init_db() -> None:
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


# Close database connections
# Call this at application shutdown
async def close_db() -> None:
    global _engine, _async_session_factory
    
    if _engine is None:
        log.warning("Database not initialized")
        return
    
    log.info("Closing database connections")
    await _engine.dispose()
    _engine = None
    _async_session_factory = None
    log.info("Database connections closed")


# Get a new database session (async context manager)
# Usage: async with get_session() as session:
#            result = await session.execute(select(Model))
#            await session.commit()
# You must explicitly call session.commit() to persist changes
def get_session() -> AsyncSession:
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    return _async_session_factory()
