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
from src.search_engine import get_search_engine
from src.i18n import get_i18n
from src.bot_utils.formatters import (
    format_welcome_message, format_help_message,
    format_language_selection, format_no_results, format_search_header,
    create_language_keyboard, format_result_message,
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
# Search logic
# ---------------------------------------------------------------------------

async def _perform_search(query_text: str, user_id: int) -> dict:
    """Embed query → pgvector top 50 → AI rerank → top 5."""
    start = datetime.now()
    results = await get_search_engine().search(query_text, limit=5)
    elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)

    try:
        async with get_session() as session:
            session.add(SearchAnalytics(
                user_id=user_id, query_text=query_text,
                results_count=len(results), response_time_ms=elapsed_ms,
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


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

@router.message(SearchStates.waiting_for_query)
async def handle_search_query(message: Message, state: FSMContext):
    await state.clear()
    if not message.text or not message.from_user:
        return
    lang = get_user_language(message.from_user.id, message.from_user.language_code)
    await _send_search_results(message, message.text.strip(), lang)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message):
    if not message.text or not message.from_user:
        return
    lang = get_user_language(message.from_user.id, message.from_user.language_code)
    await _send_search_results(message, message.text.strip(), lang)


# ---------------------------------------------------------------------------
# Callback handlers
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("lang:"))
async def handle_language_selection(callback: CallbackQuery):
    if not callback.data or not callback.from_user or not callback.message:
        return
    lang_code = callback.data.split(":")[1]
    if set_user_language(callback.from_user.id, lang_code):
        await callback.answer(get_language_success_message(lang_code))
        msg = callback.message
        if msg and not isinstance(msg, InaccessibleMessage):
            await msg.edit_text(format_welcome_message(lang_code))


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    await callback.answer()


# ---------------------------------------------------------------------------
# Daily cleanup — remove listings older than 30 days
# ---------------------------------------------------------------------------

DAYS_TO_KEEP = 30
CLEANUP_INTERVAL = 86400  # 24 hours in seconds


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
                deleted = result.rowcount
            if deleted:
                logger.info(f"Cleanup: removed {deleted} listings older than {DAYS_TO_KEEP} days")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL)


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

    cleanup_task = asyncio.create_task(_cleanup_old_listings())
    logger.success("Bot started!")
    try:
        await dp.start_polling(bot)
    finally:
        cleanup_task.cancel()
        await bot.session.close()
