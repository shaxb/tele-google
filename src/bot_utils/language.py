# Language preference management

from typing import Optional, Dict
from src.i18n import get_i18n

i18n = get_i18n()

# User language preferences (user_id -> lang_code)
user_languages: Dict[int, str] = {}


def get_user_language(user_id: int, telegram_lang: Optional[str] = None) -> str:
    """Get user's preferred language (saved or detected)"""
    # Check if user has manually selected language
    if user_id in user_languages:
        return user_languages[user_id]
    
    # Otherwise detect from Telegram settings
    return i18n.detect_language(telegram_lang)


def set_user_language(user_id: int, lang_code: str) -> bool:
    """Save user language preference"""
    if lang_code not in ['uz', 'ru', 'en']:
        return False
    
    user_languages[user_id] = lang_code
    return True


def get_language_success_message(lang_code: str) -> str:
    """Get success message for language change"""
    lang_names = {
        'uz': "🇺🇿 O'zbek",
        'ru': '🇷🇺 Русский',
        'en': '🇬🇧 English'
    }
    
    success_messages = {
        'uz': f"✅ Til o'zgartirildi: {lang_names[lang_code]}",
        'ru': f"✅ Язык изменен: {lang_names[lang_code]}",
        'en': f"✅ Language changed: {lang_names[lang_code]}"
    }
    
    return success_messages.get(lang_code, "✅ Language changed")
