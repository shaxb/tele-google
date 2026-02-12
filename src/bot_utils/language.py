"""Per-user language preference management."""

from typing import Dict, Optional
from src.i18n import get_i18n

_i18n = get_i18n()
_prefs: Dict[int, str] = {}

SUPPORTED = ("uz", "ru", "en")


def get_user_language(user_id: int, telegram_lang: Optional[str] = None) -> str:
    """Return saved preference for *user_id*, else detect from Telegram."""
    if user_id in _prefs:
        return _prefs[user_id]
    return _i18n.detect_language(telegram_lang)


def set_user_language(user_id: int, lang_code: str) -> bool:
    if lang_code not in SUPPORTED:
        return False
    _prefs[user_id] = lang_code
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
