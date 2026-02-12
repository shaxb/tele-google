"""
Backfill script - Fetch historical messages from channels
Usage:
    python backfill.py --limit 20           # Last 20 messages from all channels
    python backfill.py --limit 100          # Last 100 messages
    python backfill.py --channel @MalikaBozor --limit 50  # Specific channel
"""

import asyncio
import argparse
from loguru import logger
from src.crawler import TelegramCrawler
from src.database.connection import init_db


async def main():
    parser = argparse.ArgumentParser(description='Backfill historical messages from Telegram channels')
    parser.add_argument('--limit', type=int, default=20, help='Number of messages to fetch per channel (default: 20)')
    parser.add_argument('--channel', type=str, help='Specific channel to backfill (e.g., @MalikaBozor)')
    parser.add_argument('--min-id', type=int, default=0, help='Minimum message ID to fetch from (default: 0)')
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("BACKFILL SCRIPT - Fetching Historical Messages")
    logger.info("="*80)
    logger.info(f"Limit: {args.limit} messages per channel")
    logger.info(f"Min ID: {args.min_id}")
    
    # Initialize database first
    await init_db()
    
    # Initialize crawler
    crawler = TelegramCrawler()
    await crawler.initialize_clients()
    
    if args.channel:
        # Backfill specific channel
        logger.info(f"Backfilling channel: {args.channel}")
        count = await crawler.backfill_channel(args.channel, limit=args.limit, min_id=args.min_id)
        logger.success(f"✅ Backfill complete: {count} messages indexed from {args.channel}")
    else:
        # Backfill all channels from channels.txt
        channels = crawler.load_monitored_channels()
        
        if not channels:
            logger.error("No channels found in channels.txt")
            return
        
        logger.info(f"Backfilling {len(channels)} channels...")
        
        total_count = 0
        for channel in channels:
            logger.info(f"\n📥 Backfilling {channel}...")
            count = await crawler.backfill_channel(channel, limit=args.limit, min_id=args.min_id)
            total_count += count
            logger.info(f"   → {count} messages indexed")
            await asyncio.sleep(2)  # Pause between channels
        
        logger.success(f"\n✅ BACKFILL COMPLETE")
        logger.success(f"Total messages indexed: {total_count}")
        logger.success(f"Channels processed: {len(channels)}")
    
    # Stop crawler
    await crawler.stop()


if __name__ == "__main__":
    asyncio.run(main())
