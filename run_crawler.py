"""Run the Telegram crawler"""
import asyncio
from src.crawler import TelegramCrawler
from src.database.connection import init_db

async def main():
    # Initialize database
    await init_db()
    
    # Create and start crawler
    crawler = TelegramCrawler()
    await crawler.initialize_clients()  # Initialize Telegram clients first
    await crawler.join_channels()       # Join all channels from database
    await crawler.start_monitoring()    # Start monitoring for new messages

if __name__ == "__main__":
    asyncio.run(main())
