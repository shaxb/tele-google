"""Admin-only bot commands: channel management and backfill."""

import os
import time
from functools import wraps
from pathlib import Path
from typing import List

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select, func, delete

from src.config import get_config
from src.database import get_session
from src.database.models import Listing
from src.database.repository import ChannelRepository
from src.utils.channels import load_channels, save_channels

router = Router(name="admin")
config = get_config()


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def admin_only(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user or message.from_user.id not in config.bot.admin_user_ids:
            await message.answer("❌ Admin only.")
            return
        return await func(message, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Backfill helper (creates a temporary Telethon client)
# ---------------------------------------------------------------------------

async def _run_backfill(channel_username: str, limit: int = 50) -> int:
    from telethon import TelegramClient
    from src.crawler import TelegramCrawler

    sessions_dir = Path("data/sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)
    temp_session = str(sessions_dir / f"temp_backfill_{int(time.time())}")

    client = TelegramClient(temp_session, config.telegram.api_id, config.telegram.api_hash)
    try:
        await client.connect()  # type: ignore[misc]
        if not await client.is_user_authorized():  # type: ignore[misc]
            await client.start(phone=config.telegram.phone)  # type: ignore[misc]

        crawler = TelegramCrawler()
        crawler.clients = [client]
        return await crawler.backfill_channel(channel_username, limit=limit)
    finally:
        client.disconnect()  # type: ignore[unused-coroutine]
        for ext in ("", ".session", "-journal"):
            try:
                os.remove(f"{temp_session}{ext}")
            except FileNotFoundError:
                pass


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@router.message(Command("addchannel"))
@admin_only
async def cmd_add_channel(message: Message):
    if not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📝 <b>Usage:</b> <code>/addchannel @channelname</code>")
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        channel = f"@{channel}"

    current = load_channels()
    if channel in current:
        await message.answer(f"ℹ️ {channel} is already monitored.")
        return

    status = await message.answer(f"⏳ Adding {channel} and backfilling 50 messages…")
    try:
        current.append(channel)
        save_channels(current)
        indexed = await _run_backfill(channel, limit=50)
        await status.edit_text(
            f"✅ <b>Channel added!</b>\n\n"
            f"📊 {channel}\n📥 Indexed: {indexed} messages\n"
            f"🔄 Crawler will pick it up automatically."
        )
        logger.success(f"Admin {message.from_user.id} added {channel} ({indexed} msgs)")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Failed to add {channel}: {e}")
        await status.edit_text(f"❌ Failed to add channel\n\n<code>{_esc(e)}</code>")


@router.message(Command("removechannel"))
@admin_only
async def cmd_remove_channel(message: Message):
    if not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b> <code>/removechannel @channelname</code>\n"
            "⚠️ This deletes all listings from this channel!"
        )
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        channel = f"@{channel}"

    current = load_channels()
    if channel not in current:
        await message.answer(f"ℹ️ {channel} is not monitored.")
        return

    status = await message.answer(f"⏳ Removing {channel}…")
    try:
        async with get_session() as session:
            count = (await session.execute(
                select(func.count()).select_from(Listing).where(Listing.source_channel == channel)
            )).scalar() or 0

        current.remove(channel)
        save_channels(current)
        await ChannelRepository.deactivate(channel)

        async with get_session() as session:
            await session.execute(delete(Listing).where(Listing.source_channel == channel))
            await session.commit()

        await status.edit_text(
            f"✅ <b>Channel removed!</b>\n\n📊 {channel}\n🗑️ Deleted: {count} listings"
        )
        logger.success(f"Admin {message.from_user.id} removed {channel} ({count} listings)")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Failed to remove {channel}: {e}")
        await status.edit_text(f"❌ Failed to remove channel\n\n<code>{_esc(e)}</code>")


@router.message(Command("listchannels"))
@admin_only
async def cmd_list_channels(message: Message):
    status = await message.answer("⏳ Loading…")
    try:
        channels = load_channels()
        if not channels:
            await status.edit_text("📝 No channels monitored.")
            return

        stats: List[tuple] = []
        async with get_session() as session:
            for ch in channels:
                count = (await session.execute(
                    select(func.count()).select_from(Listing).where(Listing.source_channel == ch)
                )).scalar() or 0
                stats.append((ch, count))

        total = sum(c for _, c in stats)
        lines = [f"📊 <b>Channels ({len(channels)})</b>\n"]
        for ch, count in sorted(stats, key=lambda x: x[1], reverse=True):
            lines.append(f"• {ch}: <b>{count}</b>")
        lines.append(f"\n📈 Total: {total} listings")

        await status.edit_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Failed to list channels: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


@router.message(Command("backfill"))
@admin_only
async def cmd_backfill(message: Message):
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b> <code>/backfill @channel [limit]</code>\n"
            "Default limit: 50"
        )
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        channel = f"@{channel}"
    limit = int(parts[2]) if len(parts) > 2 else 50
    if not 1 <= limit <= 1000:
        await message.answer("❌ Limit must be 1–1000")
        return

    status = await message.answer(f"⏳ Backfilling {channel} ({limit} msgs)…")
    try:
        indexed = await _run_backfill(channel, limit=limit)
        await status.edit_text(f"✅ <b>Backfill done!</b>\n\n📊 {channel}\n📥 Indexed: {indexed}/{limit}")
        logger.success(f"Admin {message.from_user.id} backfilled {channel} ({indexed}/{limit})")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Backfill failed for {channel}: {e}")
        await status.edit_text(f"❌ Backfill failed\n\n<code>{_esc(e)}</code>")


def _esc(e: Exception) -> str:
    """Escape HTML in error messages for Telegram."""
    return str(e)[:200].replace("<", "&lt;").replace(">", "&gt;")
