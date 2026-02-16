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
        f"/price - Price check / valuation\n"
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
    """Format a single search result for Telegram.

    Simple format: number + match % + raw text + link to original.
    """
    channel = result.get("source_channel", "")
    msg_id = result.get("source_message_id")
    raw_text = result.get("raw_text", "")
    similarity = result.get("similarity_score", 0)

    if not channel or not msg_id:
        return ""

    link = f"https://t.me/{channel.lstrip('@')}/{msg_id}"
    pct = int(similarity * 100)
    emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🟠"
    preview = _truncate(raw_text, 300)

    return (
        f"<b>{index}.</b> {emoji} {pct}% match\n"
        f"{_esc_html(preview)}\n"
        f"🔗 <a href='{link}'>Original message</a>"
    )


def _esc_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_valuation_result(query: str, data: Dict[str, Any]) -> str:
    """Format price check / valuation result."""
    cur = data["currency"]

    def _fmt_price(p: float) -> str:
        if cur == "USD":
            return f"${p:,.0f}"
        if cur == "UZS":
            return f"{p:,.0f} сўм"
        return f"{p:,.0f} {cur}"

    median = _fmt_price(data["median_price"])
    mean = _fmt_price(data["mean_price"])
    low = _fmt_price(data["min_price"])
    high = _fmt_price(data["max_price"])
    spread = data.get("price_range_pct", 0)
    count = data["sample_count"]

    lines = [
        f"💰 <b>Price Check: {_esc_html(query)}</b>\n",
        f"📊 Based on <b>{count}</b> similar listings\n",
        f"🎯 <b>Fair value: {median}</b>",
        f"📈 Average: {mean}",
        f"📉 Range: {low} – {high}",
        f"📐 Spread: {spread:.0f}%\n",
    ]

    # Show sample listings
    samples = data.get("sample_listings", [])
    if samples:
        lines.append("📋 <b>Comparable listings:</b>")
        for s in samples:
            title = s.get("title", "?")
            price = s.get("price", 0)
            ch = s.get("channel", "?")
            mid = s.get("message_id")
            p_str = _fmt_price(price)
            if mid and ch:
                link = f"https://t.me/{ch.lstrip('@')}/{mid}"
                lines.append(f"  • {_esc_html(title)} — {p_str} <a href='{link}'>→</a>")
            else:
                lines.append(f"  • {_esc_html(title)} — {p_str}")

    lines.append(f"\n💡 <i>Prices based on recent marketplace listings</i>")
    return "\n".join(lines)

