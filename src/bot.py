# Telegram Bot - Search interface
# Simple: user sends query → embed → pgvector → AI rerank → return 5 results

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List
from functools import wraps

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from loguru import logger
from sqlalchemy import select, func, delete

from src.config import get_config
from src.database import init_db, get_session
from src.database.models import SearchAnalytics, Listing
from src.database.repository import ChannelRepository
from src.search_engine import get_search_engine
from src.utils.helpers import truncate_text
from src.i18n import get_i18n
from src.bot_utils.formatters import (
    format_welcome_message, format_help_message, format_stats_message,
    format_language_selection, format_no_results, format_search_header,
    create_language_keyboard
)
from src.bot_utils.language import get_user_language, set_user_language, get_language_success_message


# Config
config = get_config()
bot = Bot(token=config.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router(name="main")
i18n = get_i18n()

# Channels file path
CHANNELS_FILE = Path("channels.txt")


# States
class SearchStates(StatesGroup):
    waiting_for_query = State()


# ============================================================================
# ADMIN UTILITIES
# ============================================================================

def admin_only(func):
    """Decorator to restrict commands to admin users only"""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user:
            return
        
        if message.from_user.id not in config.bot.admin_user_ids:
            await message.answer("❌ This command is only available to administrators.")
            logger.warning(f"Unauthorized admin command attempt by user {message.from_user.id}")
            return
        
        return await func(message, *args, **kwargs)
    return wrapper


def load_channels_from_file() -> List[str]:
    """Load monitored channels from channels.txt"""
    if not CHANNELS_FILE.exists():
        return []
    
    channels = []
    with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                channels.append(line)
    return channels


def save_channels_to_file(channels: List[str]) -> None:
    """Save monitored channels to channels.txt"""
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        f.write("# Monitored Telegram Channels\n")
        f.write("# Add one channel username per line (with or without @)\n\n")
        for channel in channels:
            f.write(f"{channel}\n")
    logger.info(f"Saved {len(channels)} channels to {CHANNELS_FILE}")


async def run_backfill_for_channel(channel_username: str, limit: int = 50) -> int:
    """Run backfill for a specific channel using a temporary client"""
    from telethon import TelegramClient
    from pathlib import Path
    import time
    
    try:
        logger.info(f"Starting backfill for {channel_username} (limit: {limit})")
        
        # Create a temporary session for backfill (won't conflict with running crawler)
        sessions_dir = Path("data/sessions")
        sessions_dir.mkdir(parents=True, exist_ok=True)
        temp_session = str(sessions_dir / f"temp_backfill_{int(time.time())}")
        
        # Create temporary client
        client = TelegramClient(
            temp_session,
            config.telegram.api_id,
            config.telegram.api_hash
        )
        
        await client.connect()
        if not await client.is_user_authorized():
            await client.start(phone=config.telegram.phone)
        
        logger.info(f"Temporary client connected for backfill")
        
        # Import crawler to use its backfill logic
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler()
        crawler.clients = [client]  # Use our temporary client
        
        indexed_count = await crawler.backfill_channel(channel_username, limit=limit)
        
        # Cleanup
        await client.disconnect()
        
        # Remove temporary session files
        import os
        for ext in ['', '.session', '-journal']:
            try:
                os.remove(f"{temp_session}{ext}")
            except FileNotFoundError:
                pass
        
        logger.success(f"Backfill complete: {indexed_count} messages indexed from {channel_username}")
        return indexed_count
        
    except Exception as e:
        logger.error(f"Backfill failed for {channel_username}: {e}")
        raise


# ============================================================================
# SEARCH LOGIC
# ============================================================================

async def perform_search(query_text: str, user_id: int) -> dict:
    """Embed query → pgvector top 30 → AI rerank → return top 5"""
    start_time = datetime.now()
    
    search_engine = get_search_engine()
    results = await search_engine.search(query_text, limit=5)
    
    processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    # Track analytics
    try:
        async with get_session() as session:
            analytics = SearchAnalytics(
                user_id=user_id, query_text=query_text,
                results_count=len(results), response_time_ms=processing_time_ms,
                searched_at=datetime.now()
            )
            session.add(analytics)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to track analytics: {e}")
    
    logger.info(f"Search: '{query_text}' → {len(results)} results ({processing_time_ms}ms) | user={user_id}")
    
    return {
        "results": results,
        "processing_time_ms": processing_time_ms,
    }


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not message.from_user:
        return
    # Ask user to choose language first
    welcome_text = (
        "👋 <b>Welcome to Tele-Google!</b>\n"
        "Добро пожаловать в Tele-Google!\n"
        "Tele-Google ga xush kelibsiz!\n\n"
        "Please select your language:\n"
        "Пожалуйста, выберите язык:\n"
        "Iltimos, tilni tanlang:"
    )
    await message.answer(welcome_text, reply_markup=create_language_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not message.from_user:
        return
    lang = get_user_language(message.from_user.id, message.from_user.language_code)
    await message.answer(format_help_message(lang))


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    if not message.from_user:
        return
    lang = get_user_language(message.from_user.id, message.from_user.language_code)
    await state.set_state(SearchStates.waiting_for_query)
    await message.answer(
        f"🔍 <b>{i18n.get('commands.search.title', lang)}</b>\n\n"
        f"{i18n.get('commands.search.prompt', lang)}\n\n"
        f"<i>{i18n.get('commands.search.hint', lang)}</i>"
    )





@router.message(Command("language"))
async def cmd_language(message: Message):
    if not message.from_user:
        return
    lang = get_user_language(message.from_user.id, message.from_user.language_code)
    await message.answer(format_language_selection(lang), reply_markup=create_language_keyboard())


# ============================================================================
# ADMIN COMMANDS
# ============================================================================

@router.message(Command("addchannel"))
@admin_only
async def cmd_add_channel(message: Message):
    """Add a new channel to monitoring list and backfill it"""
    if not message.text:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b>\n"
            "<code>/addchannel @channelname</code>\n\n"
            "Example: <code>/addchannel @electronics_market</code>"
        )
        return
    
    channel_username = parts[1].strip()
    
    # Normalize channel username
    if not channel_username.startswith('@'):
        channel_username = f'@{channel_username}'
    
    # Check if already exists
    current_channels = load_channels_from_file()
    if channel_username in current_channels:
        await message.answer(f"ℹ️ Channel {channel_username} is already being monitored.")
        return
    
    status_msg = await message.answer(
        f"⏳ Adding channel {channel_username}...\n\n"
        "This will:\n"
        "1️⃣ Add to monitoring list\n"
        "2️⃣ Add to database\n"
        "3️⃣ Backfill last 50 messages\n\n"
        "<i>Please wait...</i>"
    )
    
    try:
        # Add to channels.txt
        current_channels.append(channel_username)
        save_channels_to_file(current_channels)
        
        await status_msg.edit_text(
            f"✅ Channel added to monitoring list\n\n"
            f"⏳ Starting backfill (50 messages)...\n"
            f"<i>This may take a few minutes...</i>"
        )
        
        # Run backfill
        indexed_count = await run_backfill_for_channel(channel_username, limit=50)
        
        await status_msg.edit_text(
            f"✅ <b>Channel Added Successfully!</b>\n\n"
            f"📊 Channel: {channel_username}\n"
            f"📥 Indexed: {indexed_count} messages\n"
            f"🔄 Now monitoring for new messages\n\n"
            f"<i>Crawler will automatically pick it up on next run.</i>"
        )
        
        logger.success(f"Admin {message.from_user.id} added channel {channel_username} ({indexed_count} messages)")
        
    except Exception as e:
        logger.error(f"Failed to add channel {channel_username}: {e}")
        # Escape HTML entities in error message
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await status_msg.edit_text(
            f"❌ <b>Failed to add channel</b>\n\n"
            f"<code>{error_msg[:200]}</code>\n\n"
            f"Please check:\n"
            "• Channel username is correct\n"
            "• Channel exists and is public\n"
            "• Bot has access to the channel"
        )


@router.message(Command("removechannel"))
@admin_only
async def cmd_remove_channel(message: Message):
    """Remove a channel from monitoring and delete all its data"""
    if not message.text:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b>\n"
            "<code>/removechannel @channelname</code>\n\n"
            "⚠️ <b>Warning:</b> This will delete all listings from this channel!"
        )
        return
    
    channel_username = parts[1].strip()
    
    # Normalize channel username
    if not channel_username.startswith('@'):
        channel_username = f'@{channel_username}'
    
    # Check if exists
    current_channels = load_channels_from_file()
    if channel_username not in current_channels:
        await message.answer(f"ℹ️ Channel {channel_username} is not in the monitoring list.")
        return
    
    status_msg = await message.answer(
        f"⏳ Removing channel {channel_username}...\n\n"
        "This will:\n"
        "1️⃣ Remove from monitoring list\n"
        "2️⃣ Deactivate in database\n"
        "3️⃣ Delete all listings\n\n"
        "<i>Please wait...</i>"
    )
    
    try:
        # Count listings before deletion
        async with get_session() as session:
            result = await session.execute(
                select(func.count()).select_from(Listing).where(
                    Listing.source_channel == channel_username
                )
            )
            listing_count = result.scalar() or 0
        
        # Remove from channels.txt
        current_channels.remove(channel_username)
        save_channels_to_file(current_channels)
        
        # Deactivate in database
        await ChannelRepository.deactivate(channel_username)
        
        # Delete listings from PostgreSQL
        async with get_session() as session:
            await session.execute(
                delete(Listing).where(Listing.source_channel == channel_username)
            )
            await session.commit()
        
        await status_msg.edit_text(
            f"✅ <b>Channel Removed Successfully!</b>\n\n"
            f"📊 Channel: {channel_username}\n"
            f"🗑️ Deleted: {listing_count} listings\n"
            f"❌ No longer monitoring"
        )
        
        logger.success(f"Admin {message.from_user.id} removed channel {channel_username} ({listing_count} listings)")
        
    except Exception as e:
        logger.error(f"Failed to remove channel {channel_username}: {e}")
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await status_msg.edit_text(
            f"❌ <b>Failed to remove channel</b>\n\n"
            f"<code>{error_msg[:200]}</code>"
        )


@router.message(Command("listchannels"))
@admin_only
async def cmd_list_channels(message: Message):
    """List all monitored channels with statistics"""
    status_msg = await message.answer("⏳ Loading channel statistics...")
    
    try:
        channels = load_channels_from_file()
        
        if not channels:
            await status_msg.edit_text("📝 No channels are being monitored.")
            return
        
        # Get statistics for each channel
        channel_stats = []
        async with get_session() as session:
            for channel in channels:
                result = await session.execute(
                    select(func.count()).select_from(Listing).where(
                        Listing.source_channel == channel
                    )
                )
                count = result.scalar() or 0
                channel_stats.append((channel, count))
        
        # Format output
        total_listings = sum(count for _, count in channel_stats)
        
        msg = f"📊 <b>Monitored Channels ({len(channels)})</b>\n\n"
        
        for channel, count in sorted(channel_stats, key=lambda x: x[1], reverse=True):
            msg += f"• {channel}: <b>{count}</b> listings\n"
        
        msg += f"\n📈 <b>Total:</b> {total_listings} listings"
        
        await status_msg.edit_text(msg)
        
    except Exception as e:
        logger.error(f"Failed to list channels: {e}")
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await status_msg.edit_text(
            f"❌ Failed to load channel statistics\n\n"
            f"<code>{error_msg[:200]}</code>"
        )


@router.message(Command("backfill"))
@admin_only
async def cmd_backfill(message: Message):
    """Manually backfill a specific channel"""
    if not message.text:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b>\n"
            "<code>/backfill @channelname [limit]</code>\n\n"
            "Examples:\n"
            "• <code>/backfill @electronics</code> (default: 50 messages)\n"
            "• <code>/backfill @electronics 100</code> (100 messages)"
        )
        return
    
    channel_username = parts[1].strip()
    limit = int(parts[2]) if len(parts) > 2 else 50
    
    # Normalize channel username
    if not channel_username.startswith('@'):
        channel_username = f'@{channel_username}'
    
    # Validate limit
    if limit < 1 or limit > 1000:
        await message.answer("❌ Limit must be between 1 and 1000")
        return
    
    status_msg = await message.answer(
        f"⏳ <b>Starting Backfill</b>\n\n"
        f"📊 Channel: {channel_username}\n"
        f"📥 Limit: {limit} messages\n\n"
        f"<i>This may take a few minutes...</i>"
    )
    
    try:
        indexed_count = await run_backfill_for_channel(channel_username, limit=limit)
        
        await status_msg.edit_text(
            f"✅ <b>Backfill Complete!</b>\n\n"
            f"📊 Channel: {channel_username}\n"
            f"📥 Processed: {limit} messages\n"
            f"✅ Indexed: {indexed_count} listings"
        )
        
        logger.success(f"Admin {message.from_user.id} backfilled {channel_username} ({indexed_count}/{limit} messages)")
        
    except Exception as e:
        logger.error(f"Backfill failed for {channel_username}: {e}")
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await status_msg.edit_text(
            f"❌ <b>Backfill Failed</b>\n\n"
            f"<code>{error_msg[:200]}</code>"
        )


# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

@router.message(SearchStates.waiting_for_query)
async def handle_search_query(message: Message, state: FSMContext):
    await state.clear()
    await process_search_message(message)


@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: Message):
    await process_search_message(message)


async def process_search_message(message: Message):
    """Process search and send up to 5 results as text+link messages."""
    if not message.text or not message.from_user:
        return
    
    lang = get_user_language(message.from_user.id, message.from_user.language_code)
    query = message.text.strip()
    
    if not query:
        await message.answer(f"❌ {i18n.get('errors.no_query', lang)}")
        return
    
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status_msg = await message.answer(f"🔍 <i>{i18n.get('search.searching', lang)}</i>")
    
    try:
        search_result = await perform_search(query, message.from_user.id)
        results = search_result["results"]
        processing_time_ms = search_result["processing_time_ms"]
        
        await status_msg.delete()
        
        if not results:
            await message.answer(format_no_results(lang, query))
            return
        
        # Send header
        await message.answer(format_search_header(lang, len(results), query, processing_time_ms))
        
        # Send each result as text + link
        for i, result in enumerate(results, 1):
            source_channel = result.get('source_channel')
            message_id = result.get('source_message_id')
            raw_text = result.get('raw_text', '')
            similarity = result.get('similarity_score', 0)
            
            if not source_channel or not message_id:
                continue
            
            channel_name = source_channel.lstrip('@')
            message_link = f"https://t.me/{channel_name}/{message_id}"
            text_preview = truncate_text(raw_text, 300) if raw_text else "(No text)"
            
            # Show relevance score as percentage
            relevance_pct = int(similarity * 100)
            relevance_emoji = "🟢" if relevance_pct >= 80 else "🟡" if relevance_pct >= 60 else "🟠"
            
            result_msg = (
                f"📱 <b>Result {i}</b> {relevance_emoji} {relevance_pct}% match\n\n"
                f"{text_preview}\n\n"
                f"🔗 <a href='{message_link}'>View Original Message</a>\n"
                f"📍 Channel: {source_channel}"
            )
            
            try:
                await message.answer(result_msg, disable_web_page_preview=False)
            except Exception as e:
                logger.error(f"Failed to send result {i}: {e}")
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.delete()
        await message.answer(f"❌ <b>{i18n.get('errors.search_failed', lang)}</b>\n\n{i18n.get('errors.search_error', lang)}")


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data.startswith("lang:"))
async def handle_language_selection(callback: CallbackQuery):
    if not callback.data or not callback.from_user or not callback.message:
        return
    
    lang_code = callback.data.split(":")[1]
    
    if set_user_language(callback.from_user.id, lang_code):
        await callback.answer(get_language_success_message(lang_code))
        # Show welcome message after language selection
        await callback.message.edit_text(format_welcome_message(lang_code))


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    await callback.answer()


# ============================================================================
# MAIN
# ============================================================================

async def main():
    logger.info("=" * 60)
    logger.info("TELE-GOOGLE BOT")
    logger.info("=" * 60)
    
    await init_db()
    dp.include_router(router)
    
    logger.success("Bot started! Press Ctrl+C to stop.")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
