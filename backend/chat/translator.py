"""
translator.py
─────────────
Translation pipeline:

  IndicTrans2 (AI4Bharat)  ← preferred when USE_INDIC_TRANS2=true
       ↓ falls back to
  Google Translate (deep-translator)

All public functions accept & return plain str.
Internal language is always English (RAG is in English).
"""

from __future__ import annotations

import logging
from chat.config import settings

logger = logging.getLogger(__name__)

# ── IndicTrans2 optional integration ─────────────────────────────────────────

def _try_indic_trans2(text: str, src: str, tgt: str) -> str | None:
    """
    Use IndicTrans2 when available.
    Install: pip install git+https://github.com/AI4Bharat/IndicTrans2
    Download models from HuggingFace: ai4bharat/indictrans2-indic-en-1B etc.

    Returns translated string or None if unavailable / failed.
    """
    if not settings.use_indic_trans2:
        return None
    try:
        from IndicTransToolkit import IndicProcessor  # type: ignore
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # type: ignore
        import torch  # type: ignore

        # Determine model direction
        if src == "en":
            model_name = "ai4bharat/indictrans2-en-indic-1B"
        elif tgt == "en":
            model_name = "ai4bharat/indictrans2-indic-en-1B"
        else:
            # Indic→Indic: go through English as pivot
            en_text = _try_indic_trans2(text, src, "en")
            if en_text:
                return _try_indic_trans2(en_text, "en", tgt)
            return None

        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True)
        model.eval()

        # Map ISO 639-1 → IndicTrans2 language tags
        INDIC_TAG_MAP = {
            "hi": "hin_Deva", "te": "tel_Telu", "ta": "tam_Taml",
            "kn": "kan_Knda", "ml": "mal_Mlym", "mr": "mar_Deva",
            "gu": "guj_Gujr", "bn": "ben_Beng", "pa": "pan_Guru",
            "or": "ory_Orya", "ur": "urd_Arab", "as": "asm_Beng",
            "en": "eng_Latn",
        }

        src_tag = INDIC_TAG_MAP.get(src, "eng_Latn")
        tgt_tag = INDIC_TAG_MAP.get(tgt, "eng_Latn")

        ip = IndicProcessor(inference=True)
        batch = ip.preprocess_batch([text], src_lang=src_tag, tgt_lang=tgt_tag)
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True)

        with torch.no_grad():
            outputs = model.generate(**inputs, num_beams=4, max_length=512)

        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        result = ip.postprocess_batch(decoded, lang=tgt_tag)
        return result[0] if result else None

    except ImportError:
        logger.debug("IndicTrans2 not installed — using Google Translate fallback")
        return None
    except Exception as exc:
        logger.warning("IndicTrans2 error: %s — falling back to Google Translate", exc)
        return None


# ── Google Translate fallback ─────────────────────────────────────────────────

def _google_translate(text: str, src: str, tgt: str) -> str:
    """Translate via deep-translator (Google Translate backend)."""
    if src == tgt:
        return text
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        translated = GoogleTranslator(source=src, target=tgt).translate(text)
        return translated or text
    except Exception as exc:
        logger.error("Google Translate failed: %s — returning original text", exc)
        return text


# ── Public API ────────────────────────────────────────────────────────────────

def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    """
    Translate *text* from *src_lang* to *tgt_lang*.

    Language codes: ISO 639-1 (e.g. "te", "hi", "en").
    Returns original text if src == tgt.
    """
    if not text.strip() or src_lang == tgt_lang:
        return text

    # 1. Try IndicTrans2
    result = _try_indic_trans2(text, src_lang, tgt_lang)
    if result:
        logger.debug("IndicTrans2 used for %s→%s", src_lang, tgt_lang)
        return result

    # 2. Google Translate fallback
    result = _google_translate(text, src_lang, tgt_lang)
    logger.debug("Google Translate used for %s→%s", src_lang, tgt_lang)
    return result


def to_english(text: str, src_lang: str) -> str:
    """Convenience: translate any language → English."""
    return translate(text, src_lang, "en")


def from_english(text: str, tgt_lang: str) -> str:
    """Convenience: translate English → any language."""
    return translate(text, "en", tgt_lang)
