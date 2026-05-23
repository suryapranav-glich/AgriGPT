"""
language_detector.py
────────────────────
Priority chain:
  1. Unicode block scan — instantaneous, 100% accurate for Indic scripts
  2. langdetect — handles Latin-script languages (English, etc.)
  3. Hardcoded fallback → English

NOTE: UNICODE_SCRIPT_MAP is defined here (not in config.py) because it is
      purely a detection concern and not a runtime-configurable setting.
"""

from __future__ import annotations

import logging
from chat.config import LANGUAGE_MAP

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# UNICODE SCRIPT → LANGUAGE CODE MAP
#
# Each entry: (range_object, iso_639_1_code)
# Ordered by frequency of use in Indian farming context (Telugu/Hindi first)
# so the hot path exits faster.
# ─────────────────────────────────────────────────────────────────────────────

UNICODE_SCRIPT_MAP: list[tuple[range, str]] = [
    # Telugu        U+0C00–U+0C7F
    (range(0x0C00, 0x0C80), "te"),
    # Devanagari    U+0900–U+097F  (Hindi, Marathi, Sanskrit …)
    (range(0x0900, 0x0980), "hi"),
    # Tamil         U+0B80–U+0BFF
    (range(0x0B80, 0x0C00), "ta"),
    # Kannada       U+0C80–U+0CFF
    (range(0x0C80, 0x0D00), "kn"),
    # Malayalam     U+0D00–U+0D7F
    (range(0x0D00, 0x0D80), "ml"),
    # Gujarati      U+0A80–U+0AFF
    (range(0x0A80, 0x0B00), "gu"),
    # Gurmukhi      U+0A00–U+0A7F  (Punjabi)
    (range(0x0A00, 0x0A80), "pa"),
    # Bengali       U+0980–U+09FF  (also Assamese, close enough for routing)
    (range(0x0980, 0x0A00), "bn"),
    # Odia          U+0B00–U+0B7F
    (range(0x0B00, 0x0B80), "or"),
    # Arabic        U+0600–U+06FF  (Urdu)
    (range(0x0600, 0x0700), "ur"),
    # Sinhala       U+0D80–U+0DFF  — not in LANGUAGE_MAP but harmless
    (range(0x0D80, 0x0E00), "si"),
]


# ─────────────────────────────────────────────────────────────────────────────
# DETECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _detect_by_unicode(text: str) -> str | None:
    """
    Return a language code if any Indic-script codepoint is found, else None.

    Scans every character until it hits a match — typically resolves on the
    first non-ASCII character, so it's effectively O(1) for Indic input.
    """
    for char in text:
        cp = ord(char)
        for script_range, lang_code in UNICODE_SCRIPT_MAP:
            if cp in script_range:
                return lang_code
    return None


def _detect_by_langdetect(text: str) -> str:
    """
    Use langdetect for Latin-script and mixed text.

    Returns the detected ISO 639-1 code, or 'en' on failure / unknown code.
    Seeds the detector to ensure deterministic results across calls.
    """
    try:
        from langdetect import detect, DetectorFactory  # type: ignore
        DetectorFactory.seed = 42
        code = detect(text)
        # Accept only codes present in our LANGUAGE_MAP; fall back to English
        return code if code in LANGUAGE_MAP else "en"
    except Exception as exc:
        logger.warning("langdetect failed: %s — defaulting to English", exc)
        return "en"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def detect_language(text: str) -> tuple[str, str]:
    """
    Detect the language of *text*.

    Returns
    -------
    (lang_code, lang_name)
        e.g. ("te", "Telugu") or ("en", "English")

    Resolution order
    ----------------
    1. Unicode block scan — zero-cost, 100 % accurate for Indic scripts.
    2. langdetect          — handles Latin and mixed-script input.
    3. Hard fallback       — returns ("en", "English").
    """
    text = text.strip()
    if not text:
        return "en", "English"

    # Step 1 — Unicode block (Indic scripts)
    code = _detect_by_unicode(text)
    if code:
        name = LANGUAGE_MAP.get(code, "Unknown")
        logger.debug("Unicode block detected: %s (%s)", code, name)
        return code, name

    # Step 2 — langdetect (Latin / mixed)
    code = _detect_by_langdetect(text)
    name = LANGUAGE_MAP.get(code, "English")
    logger.debug("langdetect detected: %s (%s)", code, name)
    return code, name