"""Internationalization — loads locale JSON files and resolves translated text."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class I18n:
    """Manages multi-language text resources."""

    SUPPORTED = {"uz", "ru", "en"}

    def __init__(self, locales_dir: str = "src/locales", default_lang: str = "en"):
        self.default_lang = default_lang
        self.translations: Dict[str, Dict[str, Any]] = {}
        locales = Path(locales_dir)
        if not locales.exists():
            logger.warning(f"Locales directory not found: {locales}")
            return
        for f in locales.glob("*.json"):
            try:
                self.translations[f.stem] = json.loads(f.read_text("utf-8"))
                logger.info(f"Loaded locale: {f.stem}")
            except Exception as e:
                logger.error(f"Failed to load locale {f.stem}: {e}")

    def get(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        """Resolve *key* (dot-separated path) in *lang*'s translations."""
        lang = lang if lang in self.translations else self.default_lang
        node: Any = self.translations.get(lang, {})
        for part in key.split("."):
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return key
            if node is None:
                return key
        if isinstance(node, str) and kwargs:
            try:
                return node.format(**kwargs)
            except KeyError:
                return node
        return str(node) if node is not None else key

    def get_list(self, key: str, lang: Optional[str] = None) -> list:
        """Return a list value at *key*, or ``[]``."""
        lang = lang if lang in self.translations else self.default_lang
        node: Any = self.translations.get(lang, {})
        for part in key.split("."):
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return []
        return node if isinstance(node, list) else []

    def detect_language(self, user_lang_code: Optional[str]) -> str:
        """Map a Telegram ``language_code`` to a supported language."""
        if not user_lang_code:
            return self.default_lang
        base = user_lang_code.split("-")[0].lower()
        mapping = {"uz": "uz", "ru": "ru", "en": "en", "us": "en", "gb": "en"}
        detected = mapping.get(base, self.default_lang)
        return detected if detected in self.translations else self.default_lang


_instance: Optional[I18n] = None


def get_i18n() -> I18n:
    global _instance
    if _instance is None:
        _instance = I18n()
    return _instance
