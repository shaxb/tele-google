"""Backfill historical messages from monitored channels.

Usage:
    python backfill.py --limit 50
    python backfill.py --channel @MalikaBozor --limit 100
"""

import asyncio
import argparse

from loguru import logger
from src.crawler import TelegramCrawler
from src.database.connection import init_db
from src.utils.channels import load_channels


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical messages")
    parser.add_argument("--limit", type=int, default=20, help="Messages per channel (default: 20)")
    parser.add_argument("--channel", type=str, help="Specific channel (e.g. @MalikaBozor)")
    parser.add_argument("--min-id", type=int, default=0, help="Minimum message ID")
    args = parser.parse_args()

    await init_db()

    crawler = TelegramCrawler()
    await crawler.initialize_clients()

    if args.channel:
        count = await crawler.backfill_channel(args.channel, limit=args.limit, min_id=args.min_id)
        logger.success(f"Backfill done: {count} messages from {args.channel}")
    else:
        channels = load_channels()
        if not channels:
            logger.error("No channels in channels.txt")
            return

        total = 0
        for ch in channels:
            count = await crawler.backfill_channel(ch, limit=args.limit, min_id=args.min_id)
            total += count
            await asyncio.sleep(2)

        logger.success(f"Backfill complete: {total} messages from {len(channels)} channels")

    await crawler.stop()


if __name__ == "__main__":
    asyncio.run(main())
