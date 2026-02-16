"""Telegram bot — search interface for indexed listings.

User sends query → embed → pgvector → AI rerank → return results.
"""

import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from sqlalchemy import delete
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InaccessibleMessage
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from loguru import logger

from src.config import get_config
from src.database import init_db, get_session
from src.database.models import Listing, SearchAnalytics
from src.database.repository import UserRepository
from src.notifier import get_notifier
from src.search_engine import get_search_engine
from src.i18n import get_i18n
from src.bot_utils.formatters import (
    format_welcome_message, format_help_message,
    format_language_selection, format_no_results, format_search_header,
    create_language_keyboard, format_result_message, format_valuation_result,
)
from src.bot_utils.language import get_user_language, set_user_language, get_language_success_message
from src.bot_utils.admin import router as admin_router

config = get_config()
bot = Bot(token=config.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router(name="main")
i18n = get_i18n()


class SearchStates(StatesGroup):
    waiting_for_query = State()


# ---------------------------------------------------------------------------
# User tracking
# ---------------------------------------------------------------------------

async def _track_user(message: Message) -> None:
    """Upsert user from a message — fire-and-forget."""
    u = message.from_user
    if not u:
        return
    try:
        await UserRepository.upsert_from_message(
            telegram_id=u.id,
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            language_code=u.language_code,
        )
    except Exception as e:
        logger.error(f"User tracking failed: {e}")


# ---------------------------------------------------------------------------
# Search logic
# ---------------------------------------------------------------------------

async def _perform_search(query_text: str, user_id: int) -> dict:
    """Embed query → pgvector top 50 → AI rerank → top 5."""
    start = datetime.now()
    results = await get_search_engine().search(query_text, limit=5)
    elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)

    result_ids = [r.get("id") for r in results if r.get("id")]

    try:
        await UserRepository.increment_searches(user_id)
        async with get_session() as session:
            session.add(SearchAnalytics(
                user_id=user_id, query_text=query_text,
                results_count=len(results), response_time_ms=elapsed_ms,
                result_listing_ids=result_ids,
                searched_at=datetime.now(),
            ))
            await session.commit()
    except Exception as e:
        logger.error(f"Analytics tracking failed: {e}")

    return {"results": results, "processing_time_ms": elapsed_ms}


async def _send_search_results(message: Message, query: str, lang: str) -> None:
    """Run search and send formatted results."""
    if not message.from_user:
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer(f"🔍 <i>{i18n.get('search.searching', lang)}</i>")

    try:
        data = await _perform_search(query, message.from_user.id)
        results = data["results"]
        await status.delete()

        if not results:
            await message.answer(format_no_results(lang, query))
            return

        await message.answer(format_search_header(lang, len(results), query, data["processing_time_ms"]))
        for i, r in enumerate(results, 1):
            try:
                await message.answer(format_result_message(i, r), disable_web_page_preview=False)
            except Exception as e:
                logger.error(f"Failed to send result {i}: {e}")

    except Exception as e:
        logger.error(f"Search error: {e}")
        await status.delete()
        await message.answer(f"❌ <b>{i18n.get('errors.search_failed', lang)}</b>")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not message.from_user:
        return
    await _track_user(message)
    await message.answer(
        "👋 <b>Welcome to Tele-Google!</b>\n"
        "Добро пожаловать в Tele-Google!\n"
        "Tele-Google ga xush kelibsiz!\n\n"
        "Please select your language / Tilni tanlang / Выберите язык:",
        reply_markup=create_language_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not message.from_user:
        return
    await _track_user(message)
    lang = await get_user_language(message.from_user.id, message.from_user.language_code)
    await message.answer(format_help_message(lang))


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    if not message.from_user:
        return
    await _track_user(message)
    lang = await get_user_language(message.from_user.id, message.from_user.language_code)
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
    await _track_user(message)
    lang = await get_user_language(message.from_user.id, message.from_user.language_code)
    await message.answer(format_language_selection(lang), reply_markup=create_language_keyboard())


@router.message(Command("price"))
async def cmd_price(message: Message):
    """Valuation command — /price iPhone 13 128GB → returns market price range."""
    if not message.from_user or not message.text:
        return
    await _track_user(message)
    lang = await get_user_language(message.from_user.id, message.from_user.language_code)

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "💰 <b>Price Check</b>\n\n"
            "Send: <code>/price item name</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/price iPhone 13 128GB</code>\n"
            "• <code>/price Gentra 2022</code>\n"
            "• <code>/price 3 xonali kvartira</code>"
        )
        return

    query = parts[1].strip()
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer(f"💰 <i>Analyzing prices for: {query}</i>")

    try:
        result = await get_search_engine().valuate(query)
        await status.delete()

        if not result:
            await message.answer(
                f"💰 <b>Price Check</b>\n\n"
                f"Query: <i>{query}</i>\n\n"
                f"❌ Not enough price data to estimate value.\n"
                f"We need at least 3 similar listings with prices.\n\n"
                f"💡 Try a more specific or common item name."
            )
            return

        await message.answer(format_valuation_result(query, result))

    except Exception as e:
        logger.error(f"Price check error: {e}")
        await status.delete()
        await message.answer(f"❌ Price check failed.")


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

@router.message(SearchStates.waiting_for_query)
async def handle_search_query(message: Message, state: FSMContext):
    await state.clear()
    if not message.text or not message.from_user:
        return
    lang = await get_user_language(message.from_user.id, message.from_user.language_code)
    await _send_search_results(message, message.text.strip(), lang)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message):
    if not message.text or not message.from_user:
        return
    await _track_user(message)
    lang = await get_user_language(message.from_user.id, message.from_user.language_code)
    await _send_search_results(message, message.text.strip(), lang)


# ---------------------------------------------------------------------------
# Callback handlers
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("lang:"))
async def handle_language_selection(callback: CallbackQuery):
    if not callback.data or not callback.from_user or not callback.message:
        return
    lang_code = callback.data.split(":")[1]
    if await set_user_language(callback.from_user.id, lang_code):
        await callback.answer(get_language_success_message(lang_code))
        msg = callback.message
        if msg and not isinstance(msg, InaccessibleMessage):
            await msg.edit_text(format_welcome_message(lang_code))


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    await callback.answer()


# ---------------------------------------------------------------------------
# Background tasks — cleanup + periodic health reporting
# ---------------------------------------------------------------------------

DAYS_TO_KEEP = 30
CLEANUP_INTERVAL = 86400  # 24 hours
HEALTH_INTERVAL = 21600   # 6 hours


async def _cleanup_old_listings():
    """Delete listings older than DAYS_TO_KEEP days. Runs in a loop every 24h."""
    while True:
        try:
            cutoff = datetime.utcnow() - timedelta(days=DAYS_TO_KEEP)
            async with get_session() as session:
                result = await session.execute(
                    delete(Listing).where(Listing.created_at < cutoff)
                )
                await session.commit()
                deleted = result.rowcount  # type: ignore[attr-defined]
            if deleted:
                logger.info(f"Cleanup: removed {deleted} listings older than {DAYS_TO_KEEP} days")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL)


async def _periodic_health():
    """Send system health report to the log channel every 6 hours."""
    notifier = get_notifier()
    while True:
        await asyncio.sleep(HEALTH_INTERVAL)
        try:
            # System stats
            proc = await asyncio.create_subprocess_shell(
                "free -m | awk 'NR==2{printf \"RAM: %s/%sMB (%.0f%%)\", $3,$2,$3*100/$2}' && "
                "echo '' && free -m | awk 'NR==3{printf \"Swap: %s/%sMB\", $3,$2}' && "
                "echo '' && df -h / | awk 'NR==2{printf \"Disk: %s/%s (%s)\", $3,$2,$5}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            sys_info = stdout.decode().strip()

            # DB stats
            async with get_session() as session:
                from sqlalchemy import func, select
                total = (await session.execute(
                    select(func.count()).select_from(Listing)
                )).scalar() or 0
                with_price = (await session.execute(
                    select(func.count()).select_from(Listing).where(Listing.price.isnot(None))
                )).scalar() or 0

            # Pipeline metrics from notifier
            m = notifier.metrics
            seen = m.get("messages_seen", 0)
            indexed = m.get("listings_indexed", 0)
            errors = m.get("errors", 0)

            report = (
                f"<pre>{sys_info}</pre>\n\n"
                f"📦 Total: {total} listings ({with_price} with price)\n"
                f"📊 Since last report: {seen} seen, {indexed} indexed, {errors} errors"
            )
            await notifier.health_report(report)

        except Exception as e:
            logger.error(f"Health report error: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    logger.info("=" * 60)
    logger.info("TELE-GOOGLE BOT — Starting")
    logger.info("=" * 60)

    await init_db()
    dp.include_router(admin_router)
    dp.include_router(router)

    notifier = get_notifier()
    await notifier.startup("Bot")
    await notifier.start()

    cleanup_task = asyncio.create_task(_cleanup_old_listings())
    health_task = asyncio.create_task(_periodic_health())
    logger.success("Bot started!")
    try:
        await dp.start_polling(bot)
    finally:
        cleanup_task.cancel()
        health_task.cancel()
        await notifier.shutdown("Bot")
        await notifier.stop()
        await bot.session.close()
