# Message formatting utilities for bot responses

from typing import Dict, Any, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.utils.helpers import truncate_text
from src.i18n import get_i18n

i18n = get_i18n()


def create_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard"""
    buttons = [
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ],
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_welcome_message(lang: str) -> str:
    """Format welcome message for /start command"""
    examples = i18n.get_list("commands.start.examples", lang)
    examples_text = "\n".join([f"• <code>{ex}</code>" for ex in examples])
    
    return (
        f"👋 <b>{i18n.get('commands.start.title', lang)}</b>\n\n"
        f"🔍 {i18n.get('commands.start.description', lang)}\n\n"
        f"<b>{i18n.get('commands.start.how_to', lang)}</b>\n"
        f"{i18n.get('commands.start.just_send', lang)}\n\n"
        f"<b>{i18n.get('commands.start.examples_title', lang)}</b>\n"
        f"{examples_text}\n\n"
        f"<b>{i18n.get('commands.start.commands_title', lang)}</b>\n"
        f"/search - {i18n.get('commands.search.title', lang)}\n"
        f"/help - {i18n.get('commands.help.title', lang)}\n"
        f"/stats - {i18n.get('commands.stats.title', lang)}\n"
        f"/language - Change language / Tilni o'zgartirish / Сменить язык\n\n"
        f"🌐 {i18n.get('commands.start.footer', lang)}"
    )


def format_help_message(lang: str) -> str:
    """Format help message for /help command"""
    features = i18n.get_list("commands.help.features", lang)
    features_text = "\n".join([f"• {f}" for f in features])
    
    tips = i18n.get_list("commands.help.tips", lang)
    tips_text = "\n".join([f"• {t}" for t in tips])
    
    return (
        f"📖 <b>{i18n.get('commands.help.title', lang)}</b>\n\n"
        f"<b>🔍 {i18n.get('commands.help.how_to_search', lang)}</b>\n"
        f"{i18n.get('commands.help.understand', lang)}\n"
        f"{features_text}\n\n"
        f"<b>💡 {i18n.get('commands.help.tips_title', lang)}</b>\n"
        f"{tips_text}\n\n"
        f"<b>🌐 {i18n.get('commands.help.languages_title', lang)}</b>\n"
        f"• 🇺🇿 Uzbek\n"
        f"• 🇷🇺 Russian\n"
        f"• 🇬🇧 English\n\n"
        f"<b>📱 {i18n.get('commands.help.commands_title', lang)}</b>\n"
        f"/start - {i18n.get('commands.start.title', lang)}\n"
        f"/search - {i18n.get('commands.search.title', lang)}\n"
        f"/help - {i18n.get('commands.help.title', lang)}\n"
        f"/stats - {i18n.get('commands.stats.title', lang)}\n"
        f"/language - Change language"
    )


def format_stats_message(lang: str, total_searches: int, recent_searches: List) -> str:
    """Format statistics message"""
    stats_text = (
        f"📊 <b>{i18n.get('commands.stats.title', lang)}</b>\n\n"
        f"🔍 {i18n.get('commands.stats.total_searches', lang)} <b>{total_searches}</b>\n\n"
    )
    
    if recent_searches:
        stats_text += f"<b>{i18n.get('commands.stats.recent_title', lang)}</b>\n"
        for i, search in enumerate(recent_searches, 1):
            query = truncate_text(str(search.query_text), 30)
            results = search.results_count or 0
            stats_text += f"{i}. {query} ({results} {i18n.get('commands.stats.results', lang)})\n"
    else:
        stats_text += f"<i>{i18n.get('commands.stats.no_recent', lang)}</i>"
    
    return stats_text


def format_language_selection(lang: str) -> str:
    """Format language selection message"""
    lang_names = {
        'uz': "🇺🇿 O'zbek",
        'ru': '🇷🇺 Русский',
        'en': '🇬🇧 English'
    }
    
    current_name = lang_names.get(lang, '🇬🇧 English')
    
    return (
        f"🌐 <b>Language / Til / Язык</b>\n\n"
        f"Current: {current_name}\n"
        f"Joriy: {current_name}\n"
        f"Текущий: {current_name}\n\n"
        f"Select your language:\n"
        f"Tilni tanlang:\n"
        f"Выберите язык:"
    )


def format_no_results(lang: str, query: str) -> str:
    """Format no results found message"""
    tips = i18n.get_list("search.no_results.tips", lang)
    tips_text = "\n".join([f"• {tip}" for tip in tips])
    
    return (
        f"🔍 <b>{i18n.get('search.no_results.title', lang)}</b>\n\n"
        f"{i18n.get('search.query', lang)} <i>{query}</i>\n\n"
        f"💡 <b>{i18n.get('search.no_results.tips_title', lang)}</b>\n"
        f"{tips_text}"
    )


def format_search_header(lang: str, total_results: int, query: str, processing_time_ms: int) -> str:
    """Format search results header"""
    result_word = i18n.get('search.result', lang) if total_results == 1 else i18n.get('search.results', lang)
    return (
        f"🔍 <b>{i18n.get('search.found', lang)} {total_results} {result_word}</b>\n"
        f"{i18n.get('search.query', lang)} <i>{query}</i>\n"
        f"⏱ {processing_time_ms}ms\n"
    )



