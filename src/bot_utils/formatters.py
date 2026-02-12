"""Message formatting utilities for bot responses."""

from typing import Any, Dict, List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.i18n import get_i18n

i18n = get_i18n()


def _truncate(text: str, max_len: int = 300) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def create_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
    ])


def format_welcome_message(lang: str) -> str:
    examples = i18n.get_list("commands.start.examples", lang)
    examples_text = "\n".join(f"• <code>{ex}</code>" for ex in examples)
    return (
        f"👋 <b>{i18n.get('commands.start.title', lang)}</b>\n\n"
        f"🔍 {i18n.get('commands.start.description', lang)}\n\n"
        f"<b>{i18n.get('commands.start.how_to', lang)}</b>\n"
        f"{i18n.get('commands.start.just_send', lang)}\n\n"
        f"<b>{i18n.get('commands.start.examples_title', lang)}</b>\n{examples_text}\n\n"
        f"<b>{i18n.get('commands.start.commands_title', lang)}</b>\n"
        f"/search - {i18n.get('commands.search.title', lang)}\n"
        f"/help - {i18n.get('commands.help.title', lang)}\n"
        f"/language - Change language\n\n"
        f"🌐 {i18n.get('commands.start.footer', lang)}"
    )


def format_help_message(lang: str) -> str:
    features = "\n".join(f"• {f}" for f in i18n.get_list("commands.help.features", lang))
    tips = "\n".join(f"• {t}" for t in i18n.get_list("commands.help.tips", lang))
    return (
        f"📖 <b>{i18n.get('commands.help.title', lang)}</b>\n\n"
        f"<b>🔍 {i18n.get('commands.help.how_to_search', lang)}</b>\n"
        f"{i18n.get('commands.help.understand', lang)}\n{features}\n\n"
        f"<b>💡 {i18n.get('commands.help.tips_title', lang)}</b>\n{tips}\n\n"
        f"<b>📱 Commands</b>\n"
        f"/start - {i18n.get('commands.start.title', lang)}\n"
        f"/search - {i18n.get('commands.search.title', lang)}\n"
        f"/help - {i18n.get('commands.help.title', lang)}\n"
        f"/language - Change language"
    )


def format_language_selection(lang: str) -> str:
    names = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
    current = names.get(lang, "🇬🇧 English")
    return (
        f"🌐 <b>Language / Til / Язык</b>\n\n"
        f"Current: {current}\n\n"
        "Select your language / Tilni tanlang / Выберите язык:"
    )


def format_no_results(lang: str, query: str) -> str:
    tips = "\n".join(f"• {t}" for t in i18n.get_list("search.no_results.tips", lang))
    return (
        f"🔍 <b>{i18n.get('search.no_results.title', lang)}</b>\n\n"
        f"{i18n.get('search.query', lang)} <i>{query}</i>\n\n"
        f"💡 <b>{i18n.get('search.no_results.tips_title', lang)}</b>\n{tips}"
    )


def format_search_header(lang: str, total: int, query: str, ms: int) -> str:
    word = i18n.get("search.result", lang) if total == 1 else i18n.get("search.results", lang)
    return (
        f"🔍 <b>{i18n.get('search.found', lang)} {total} {word}</b>\n"
        f"{i18n.get('search.query', lang)} <i>{query}</i>\n"
        f"⏱ {ms}ms"
    )


def format_result_message(index: int, result: Dict[str, Any]) -> str:
    """Format a single search result for Telegram."""
    channel = result.get("source_channel", "")
    msg_id = result.get("source_message_id")
    raw_text = result.get("raw_text", "")
    similarity = result.get("similarity_score", 0)

    if not channel or not msg_id:
        return ""

    link = f"https://t.me/{channel.lstrip('@')}/{msg_id}"
    preview = _truncate(raw_text) if raw_text else "(No text)"
    pct = int(similarity * 100)
    emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🟠"

    return (
        f"📱 <b>Result {index}</b> {emoji} {pct}% match\n\n"
        f"{preview}\n\n"
        f"🔗 <a href='{link}'>View Original Message</a>\n"
        f"📍 Channel: {channel}"
    )

