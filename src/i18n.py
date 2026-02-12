# Internationalization (i18n) manager for multi-language support
# Loads locale files and provides text based on user's language

import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class I18n:
    """Manages multi-language text resources"""
    
    def __init__(self, locales_dir: str = "src/locales", default_lang: str = "en"):
        self.locales_dir = Path(locales_dir)
        self.default_lang = default_lang
        self.translations: Dict[str, Dict[str, Any]] = {}
        self._load_all_locales()
    
    def _load_all_locales(self):
        """Load all locale JSON files from locales directory"""
        if not self.locales_dir.exists():
            logger.warning(f"Locales directory not found: {self.locales_dir}")
            return
        
        for locale_file in self.locales_dir.glob("*.json"):
            lang_code = locale_file.stem  # en, uz, ru
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                logger.info(f"Loaded locale: {lang_code}")
            except Exception as e:
                logger.error(f"Failed to load locale {lang_code}: {e}")
    
    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Get translated text by key path (e.g., "commands.start.title")
        
        Args:
            key: Dot-separated path to text (e.g., "search.searching")
            lang: Language code (en/uz/ru), defaults to default_lang
            **kwargs: Format variables for string interpolation
        
        Returns:
            Translated text or key if not found
        """
        lang = lang or self.default_lang
        
        # Fallback to English if language not found
        if lang not in self.translations:
            logger.warning(f"Language not found: {lang}, falling back to {self.default_lang}")
            lang = self.default_lang
        
        # Navigate through nested dict using key path
        parts = key.split('.')
        current = self.translations.get(lang, {})
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    logger.warning(f"Translation key not found: {key} (lang: {lang})")
                    return key
            else:
                logger.warning(f"Invalid key path: {key} (lang: {lang})")
                return key
        
        # Handle string interpolation if kwargs provided
        if isinstance(current, str) and kwargs:
            try:
                return current.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format key {e} for: {key}")
                return current
        
        return str(current) if current is not None else key
    
    def get_list(self, key: str, lang: str = None) -> list:
        """Get a list from translations (e.g., examples, tips)"""
        lang = lang or self.default_lang
        
        if lang not in self.translations:
            lang = self.default_lang
        
        parts = key.split('.')
        current = self.translations.get(lang, {})
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return []
        
        return current if isinstance(current, list) else []
    
    def detect_language(self, user_lang_code: Optional[str]) -> str:
        """
        Detect user language from Telegram language_code
        
        Args:
            user_lang_code: Telegram user language code (e.g., "uz", "ru", "en")
        
        Returns:
            Supported language code or default
        """
        if not user_lang_code:
            return self.default_lang
        
        # Extract base language (e.g., "en-US" -> "en")
        base_lang = user_lang_code.split('-')[0].lower()
        
        # Map common codes
        lang_map = {
            'uz': 'uz',
            'ru': 'ru',
            'en': 'en',
            'us': 'en',
            'gb': 'en',
        }
        
        detected = lang_map.get(base_lang, self.default_lang)
        
        # Verify language is available
        if detected not in self.translations:
            return self.default_lang
        
        return detected


# Global instance
_i18n = None


def get_i18n() -> I18n:
    """Get global i18n instance (singleton pattern)"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n
