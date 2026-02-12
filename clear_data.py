"""Truncate the listings table. Use with caution."""

import asyncio
from loguru import logger
from sqlalchemy import text
from src.database.connection import init_db, get_session


async def main() -> None:
    await init_db()
    async with get_session() as session:
        await session.execute(text("TRUNCATE TABLE listings RESTART IDENTITY CASCADE;"))
        await session.commit()
    logger.success("Listings table cleared")


if __name__ == "__main__":
    asyncio.run(main())
