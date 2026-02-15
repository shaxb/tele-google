"""Per-user language preference management — DB-backed with in-memory cache."""

from typing import Dict, Optional
from src.i18n import get_i18n
from src.database.repository import UserRepository

_i18n = get_i18n()
_cache: Dict[int, str] = {}  # in-memory cache, populated from DB on first access

SUPPORTED = ("uz", "ru", "en")


async def get_user_language(user_id: int, telegram_lang: Optional[str] = None) -> str:
    """Return saved preference for *user_id*, else detect from Telegram."""
    if user_id in _cache:
        return _cache[user_id]
    # Try DB
    db_pref = await UserRepository.get_preferred_language(user_id)
    if db_pref and db_pref in SUPPORTED:
        _cache[user_id] = db_pref
        return db_pref
    return _i18n.detect_language(telegram_lang)


async def set_user_language(user_id: int, lang_code: str) -> bool:
    if lang_code not in SUPPORTED:
        return False
    _cache[user_id] = lang_code
    await UserRepository.set_preferred_language(user_id, lang_code)
    return True


_LANG_NAMES = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
_SUCCESS = {
    "uz": "✅ Til o'zgartirildi: {name}",
    "ru": "✅ Язык изменен: {name}",
    "en": "✅ Language changed: {name}",
}


def get_language_success_message(lang_code: str) -> str:
    tpl = _SUCCESS.get(lang_code, "✅ Language changed: {name}")
    return tpl.format(name=_LANG_NAMES.get(lang_code, lang_code))
