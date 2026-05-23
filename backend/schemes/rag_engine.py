# =============================================================================
# AgriGPT — Government Schemes Q&A
# schemes/rag_engine.py  (Fixed v3)
#
# FIXES from v2:
#   - Removed signal.alarm() — only works on main thread, crashes in executor
#   - Timeout is handled by asyncio.wait_for() in router instead
#   - Cleaner error handling
# =============================================================================

import os
import re
import json
import textwrap
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LLM_MODEL = "gemini-2.5-flash"

_llm           = None
_vector_db     = "none"
_engine_loaded = False


# =============================================================================
# PROMPT BUILDER
# =============================================================================
def _get_prompt(language: str, context: str, question: str) -> str:
    if language == "hi":
        return textwrap.dedent(f"""
        आप AgriGPT के सरकारी योजना सहायक हैं। किसानों को सरल हिंदी में बताएं।

        संदर्भ:
        {context}

        किसान का प्रश्न: {question}

        केवल valid JSON object दें (कोई markdown नहीं, JSON के बाहर कोई text नहीं):
        {{
          "answer": "<3-5 वाक्यों में उत्तर>",
          "scheme_name": "<योजना का नाम>",
          "eligibility": "<पात्रता>",
          "how_to_apply": "<आवेदन कैसे करें>",
          "documents_needed": ["<दस्तावेज़ 1>", "<दस्तावेज़ 2>"],
          "helpline": "<हेल्पलाइन नंबर>",
          "amount_or_benefit": "<राशि या लाभ>",
          "state_specific": "<राज्य विशेष जानकारी>",
          "sources": ["<स्रोत>"],
          "tip": "<एक त्वरित सुझाव>"
        }}
        """).strip()

    elif language == "te":
        return textwrap.dedent(f"""
        మీరు AgriGPT సహాయకులు. రైతులకు సరళమైన తెలుగులో సమాధానం ఇవ్వండి.

        సమాచారం:
        {context}

        రైతు ప్రశ్న: {question}

        కేవలం valid JSON మాత్రమే ఇవ్వండి (markdown వద్దు):
        {{
          "answer": "<3-5 వాక్యాలు>",
          "scheme_name": "<పథకం పేరు>",
          "eligibility": "<అర్హత>",
          "how_to_apply": "<దరఖాస్తు విధానం>",
          "documents_needed": ["<పత్రం 1>", "<పత్రం 2>"],
          "helpline": "<హెల్ప్‌లైన్>",
          "amount_or_benefit": "<మొత్తం>",
          "state_specific": "<రాష్ట్ర సమాచారం>",
          "sources": ["<వనరు>"],
          "tip": "<సూచన>"
        }}
        """).strip()

    else:
        return textwrap.dedent(f"""
        You are AgriGPT's Government Schemes Assistant for Indian farmers.
        Focus on Telangana and Andhra Pradesh. Be concise and farmer-friendly.

        CONTEXT:
        {context}

        FARMER'S QUESTION: {question}

        Reply ONLY with a valid JSON object.
        No markdown fences. No text before or after the JSON.

        {{
          "answer": "<clear 3-5 sentence answer>",
          "scheme_name": "<primary scheme name>",
          "eligibility": "<who qualifies>",
          "how_to_apply": "<step-by-step process>",
          "documents_needed": ["<doc1>", "<doc2>"],
          "helpline": "<helpline number or URL>",
          "amount_or_benefit": "<amount or subsidy benefit>",
          "state_specific": "<Telangana or AP note, or 'Applies across India'>",
          "sources": ["<source name>"],
          "tip": "<one quick action tip>"
        }}
        """).strip()


# =============================================================================
# STARTUP
# =============================================================================
def load_schemes_engine():
    """Initialise Gemini only. No embedder. No FAISS. No OOM."""
    global _llm, _vector_db, _engine_loaded

    if _engine_loaded:
        return

    _vector_db = "none"

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set in Render Environment Variables."
        )

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    _llm = genai.GenerativeModel(
        LLM_MODEL,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=800,
            temperature=0.1,
        )
    )
    logger.info("[Schemes RAG] Gemini ready: %s", LLM_MODEL)
    _engine_loaded = True


# =============================================================================
# STATIC KB CONTEXT
# =============================================================================
def _static_context(question: str, state: str, language: str) -> str:
    try:
        from schemes.static_kb import search_static
        hits = search_static(question, state=state, top_k=3)
    except Exception as e:
        logger.error("[Schemes RAG] static_kb error: %s", e)
        hits = []

    if not hits:
        return "No matching static KB entries found. Use your general knowledge about Indian government agricultural schemes."

    parts = []
    for e in hits:
        if language == "hi":
            content = e.get("content_hi", e.get("content_en", ""))
        elif language == "te":
            content = e.get("content_te", e.get("content_en", ""))
        else:
            content = e.get("content_en", "")
        parts.append(
            f"[{e['name']} | {e['type']}]\n{content.strip()}\nSource: {e['source']}"
        )
    return "\n\n---\n\n".join(parts)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def ask(
    question: str,
    state   : str = "",
    language: str = "en",
) -> dict:
    """
    Schemes Q&A — called from router via asyncio.to_thread().
    No signal.alarm() here — timeout handled by asyncio.wait_for() in router.
    """
    global _llm, _engine_loaded

    if not _engine_loaded:
        load_schemes_engine()
    if _llm is None:
        load_schemes_engine()

    language = language if language in ("en", "hi", "te") else "en"

    # Build context
    context    = _static_context(question, state, language)
    enriched_q = question
    if state:
        enriched_q += f"\n[Farmer's state: {state}]"

    prompt = _get_prompt(language, context, enriched_q)

    # Call Gemini (sync — safe because router uses asyncio.to_thread)
    import google.generativeai as genai
    response = _llm.generate_content(prompt)
    raw      = response.text.strip()

    # Strip accidental markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)
    raw = raw.strip()

    # Parse JSON
    result = json.loads(raw)

    result["_meta"] = {
        "vector_db"      : _vector_db,
        "pdf_chunks_used": 0,
        "static_hits"    : 1,
        "llm_model"      : LLM_MODEL,
        "language"       : language,
        "state"          : state or "general",
    }

    return result