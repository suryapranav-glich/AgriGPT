"""
language_detector.py
────────────────────
Priority chain:
  1. Unicode block scan — instantaneous, 100% accurate for Indic scripts
  2. langdetect — handles Latin-script languages (English, etc.)
  3. Hardcoded fallback → English
"""

from __future__ import annotations

import logging
from chat.config import LANGUAGE_MAP, UNICODE_SCRIPT_MAP

logger = logging.getLogger(__name__)


def _detect_by_unicode(text: str) -> str | None:
    """Return lang_code if any Indic-script codepoint found, else None."""
    for char in text:
        cp = ord(char)
        for script_range, lang_code in UNICODE_SCRIPT_MAP:
            if cp in script_range:
                return lang_code
    return None


def _detect_by_langdetect(text: str) -> str:
    """Use langdetect for Latin-based scripts; returns 'en' on failure."""
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42          # deterministic results
        code = detect(text)
        # langdetect uses ISO 639-1; map uncommon codes to 'en'
        return code if code in LANGUAGE_MAP else "en"
    except Exception as exc:
        logger.warning("langdetect failed: %s — defaulting to English", exc)
        return "en"


def detect_language(text: str) -> tuple[str, str]:
    """
    Detect the language of *text*.

    Returns
    -------
    (lang_code, lang_name)  e.g. ("te", "Telugu")
    """
    text = text.strip()
    if not text:
        return "en", "English"

    # 1. Unicode block — most reliable for Indic scripts
    code = _detect_by_unicode(text)
    if code:
        return code, LANGUAGE_MAP.get(code, "Unknown")

    # 2. langdetect for Latin + mixed
    code = _detect_by_langdetect(text)
    return code, LANGUAGE_MAP.get(code, "English")
