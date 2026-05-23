"""
translator.py
─────────────
Translation pipeline:

  IndicTrans2 (AI4Bharat)  ← preferred when env var USE_INDIC_TRANS2=true
       ↓ falls back to
  Google Translate (deep-translator)

All public functions accept & return plain str.
Internal language is always English (RAG is in English).

NOTE: settings.use_indic_trans2 is intentionally NOT read from the
      Pydantic Settings class because that field is absent from config.py.
      Instead we read the env var directly with a safe default of False,
      so the pipeline works out-of-the-box without any .env changes.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Read once at import time; set USE_INDIC_TRANS2=true in .env to enable.
_USE_INDIC_TRANS2: bool = os.getenv("USE_INDIC_TRANS2", "false").lower() == "true"

# IndicTrans2 language tag map (ISO 639-1 → IndicTrans2 flores tag)
_INDIC_TAG_MAP: dict[str, str] = {
    "hi": "hin_Deva",
    "te": "tel_Telu",
    "ta": "tam_Taml",
    "kn": "kan_Knda",
    "ml": "mal_Mlym",
    "mr": "mar_Deva",
    "gu": "guj_Gujr",
    "bn": "ben_Beng",
    "pa": "pan_Guru",
    "or": "ory_Orya",
    "ur": "urd_Arab",
    "as": "asm_Beng",
    "en": "eng_Latn",
}


# ─────────────────────────────────────────────────────────────────────────────
# IndicTrans2 (optional)
# ─────────────────────────────────────────────────────────────────────────────

def _try_indic_trans2(text: str, src: str, tgt: str) -> str | None:
    """
    Attempt translation via IndicTrans2.

    Returns the translated string, or None if:
      • USE_INDIC_TRANS2 env var is not 'true'
      • IndicTrans2 / transformers are not installed
      • Any runtime error occurs

    Install:
        pip install git+https://github.com/AI4Bharat/IndicTrans2
    Models:
        ai4bharat/indictrans2-en-indic-1B   (English → Indic)
        ai4bharat/indictrans2-indic-en-1B   (Indic   → English)
    """
    if not _USE_INDIC_TRANS2:
        return None

    # Indic → Indic: pivot through English
    if src != "en" and tgt != "en":
        en_text = _try_indic_trans2(text, src, "en")
        if en_text:
            return _try_indic_trans2(en_text, "en", tgt)
        return None

    model_name = (
        "ai4bharat/indictrans2-en-indic-1B"
        if src == "en"
        else "ai4bharat/indictrans2-indic-en-1B"
    )

    try:
        from IndicTransToolkit import IndicProcessor  # type: ignore
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # type: ignore
        import torch  # type: ignore

        tokenizer = AutoTokenizer.from_pretrained(
            model_name, trust_remote_code=True
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name, trust_remote_code=True
        )
        model.eval()

        src_tag = _INDIC_TAG_MAP.get(src, "eng_Latn")
        tgt_tag = _INDIC_TAG_MAP.get(tgt, "eng_Latn")

        ip = IndicProcessor(inference=True)
        batch = ip.preprocess_batch([text], src_lang=src_tag, tgt_lang=tgt_tag)
        inputs = tokenizer(
            batch, return_tensors="pt", padding=True, truncation=True
        )

        with torch.no_grad():
            outputs = model.generate(**inputs, num_beams=4, max_length=512)

        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        result = ip.postprocess_batch(decoded, lang=tgt_tag)
        return result[0] if result else None

    except ImportError:
        logger.debug(
            "IndicTrans2 / transformers not installed — using Google Translate fallback"
        )
        return None
    except Exception as exc:
        logger.warning(
            "IndicTrans2 error: %s — falling back to Google Translate", exc
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Google Translate fallback
# ─────────────────────────────────────────────────────────────────────────────

def _google_translate(text: str, src: str, tgt: str) -> str:
    """
    Translate via deep-translator (Google Translate backend).

    Returns original text unchanged if:
      • src == tgt
      • deep-translator is not installed
      • Google Translate returns an empty result
    """
    if src == tgt:
        return text
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        translated = GoogleTranslator(source=src, target=tgt).translate(text)
        return translated or text
    except Exception as exc:
        logger.error(
            "Google Translate failed (%s→%s): %s — returning original text",
            src, tgt, exc,
        )
        return text


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    """
    Translate *text* from *src_lang* to *tgt_lang*.

    Language codes follow ISO 639-1 (e.g. "te", "hi", "en").
    Returns original text unchanged if src_lang == tgt_lang or text is blank.

    Resolution order
    ----------------
    1. IndicTrans2  — if USE_INDIC_TRANS2=true and package is installed
    2. Google Translate (deep-translator) — always-available fallback
    """
    if not text.strip() or src_lang == tgt_lang:
        return text

    # 1. IndicTrans2
    result = _try_indic_trans2(text, src_lang, tgt_lang)
    if result:
        logger.debug("IndicTrans2 used: %s → %s", src_lang, tgt_lang)
        return result

    # 2. Google Translate
    result = _google_translate(text, src_lang, tgt_lang)
    logger.debug("Google Translate used: %s → %s", src_lang, tgt_lang)
    return result


def to_english(text: str, src_lang: str) -> str:
    """Convenience wrapper: translate any language → English."""
    return translate(text, src_lang, "en")


def from_english(text: str, tgt_lang: str) -> str:
    """Convenience wrapper: translate English → any language."""
    return translate(text, "en", tgt_lang)