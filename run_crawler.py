"""Run the Telegram channel crawler."""

import asyncio
from src.crawler import TelegramCrawler

if __name__ == "__main__":
    asyncio.run(TelegramCrawler().start())
