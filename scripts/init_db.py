#!/usr/bin/env python
"""
Database Initialization Script
Runs migrations and initializes Meilisearch index
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import init_db, close_db
from src.search import get_search_engine
from src.utils.logger import get_logger

log = get_logger(__name__)


async def main():
    """Initialize database and search index"""
    try:
        log.info("=" * 60)
        log.info("DATABASE INITIALIZATION")
        log.info("=" * 60)
        
        # 1. Initialize PostgreSQL
        log.info("Step 1: Initializing PostgreSQL database...")
        await init_db()
        log.info("✓ PostgreSQL initialized successfully")
        
        # 2. Initialize Meilisearch
        log.info("\nStep 2: Initializing Meilisearch index...")
        search_engine = get_search_engine()
        await search_engine.initialize_index()
        
        # Get index stats
        stats = await search_engine.get_stats()
        log.info(f"✓ Meilisearch index configured")
        log.info(f"  - Index: {search_engine.index_name}")
        log.info(f"  - Documents: {stats.number_of_documents}")
        
        log.info("\n" + "=" * 60)
        log.info("INITIALIZATION COMPLETE")
        log.info("=" * 60)
        log.info("\nNext steps:")
        log.info("1. Run Alembic migrations: alembic upgrade head")
        log.info("2. Start crawler: python src/crawler.py")
        log.info("3. Start bot: python src/bot.py")
        
    except Exception as e:
        log.error(f"Initialization failed: {e}")
        raise
    finally:
        # Close database connections
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
