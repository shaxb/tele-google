# Clear all data from PostgreSQL
import asyncio
from loguru import logger
from src.database.connection import init_db, get_session
from sqlalchemy import text

async def clear_all():
    """Drop all listing data and reset"""
    await init_db()
    
    async with get_session() as session:
        await session.execute(text("TRUNCATE TABLE listings RESTART IDENTITY CASCADE;"))
        await session.commit()
        logger.success("✅ PostgreSQL listings cleared")

if __name__ == "__main__":
    asyncio.run(clear_all())
