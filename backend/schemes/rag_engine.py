# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/rag_engine.py  (Fixed v2 — timeout + async safe)
#
# FIXES:
#   1. No HuggingFaceEmbeddings / sentence_transformers (OOM fix)
#   2. Gemini call has 30s timeout (no more infinite hang)
#   3. _engine_loaded flag prevents double init
#   4. Removed langchain_classic (invalid package)
# =============================================================================

import os
import re
import json
import textwrap
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR   = Path(__file__).resolve().parent.parent
FAISS_DIR  = BASE_DIR / "data" / "scheme_faiss"
CHROMA_DIR = BASE_DIR / "data" / "scheme_chroma"

LLM_MODEL  = "gemini-1.5-flash"   # More reliable free-tier than 2.5-flash
TOP_K      = 5

# ── Singletons ────────────────────────────────────────────────────────────────
_retriever     = None
_embeddings    = None
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

        केवल valid JSON object दें (कोई markdown नहीं):
        {{
          "answer": "<3-5 वाक्यों में उत्तर>",
          "scheme_name": "<योजना का नाम>",
          "eligibility": "<पात्रता>",
          "how_to_apply": "<आवेदन कैसे करें>",
          "documents_needed": ["<दस्तावेज़ 1>", "<दस्तावेज़ 2>"],
          "helpline": "<हेल्पलाइन>",
          "amount_or_benefit": "<राशि>",
          "state_specific": "<राज्य विशेष जानकारी>",
          "sources": ["<स्रोत>"],
          "tip": "<सुझाव>"
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
          "documents_needed": ["<పత్రం 1>"],
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
        Focus on Telangana and Andhra Pradesh schemes. Be concise and farmer-friendly.

        CONTEXT:
        {context}

        FARMER'S QUESTION: {question}

        Reply ONLY with a valid JSON object (no markdown, no text outside JSON):
        {{
          "answer": "<clear 3-5 sentence answer>",
          "scheme_name": "<primary scheme name>",
          "eligibility": "<who qualifies>",
          "how_to_apply": "<step-by-step>",
          "documents_needed": ["<doc1>", "<doc2>"],
          "helpline": "<number or URL>",
          "amount_or_benefit": "<amount or benefit>",
          "state_specific": "<state-specific note>",
          "sources": ["<source>"],
          "tip": "<one quick tip>"
        }}
        """).strip()


# =============================================================================
# STARTUP
# =============================================================================
def load_schemes_engine():
    """Initialise Gemini. Skip heavy embedder — use static KB only."""
    global _llm, _vector_db, _engine_loaded

    if _engine_loaded:
        return

    # Skip embedder entirely — no FAISS/ChromaDB needed for static KB
    _vector_db = "none"
    logger.info("[Schemes RAG] Using static KB only (no FAISS/embedder).")

    # Gemini client
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set in Render Environment Variables."
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
    logger.info(f"[Schemes RAG] Gemini ready: {LLM_MODEL}")
    _engine_loaded = True


# =============================================================================
# STATIC KB CONTEXT
# =============================================================================
def _static_context(question: str, state: str, language: str) -> str:
    from schemes.static_kb import search_static
    hits = search_static(question, state=state, top_k=3)
    if not hits:
        return "No matching static KB entries found. Answer from general knowledge."
    parts = []
    for e in hits:
        if language == "hi":
            content = e.get("content_hi", e["content_en"])
        elif language == "te":
            content = e.get("content_te", e["content_en"])
        else:
            content = e["content_en"]
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
    Schemes Q&A:
      1. Load engine if not yet loaded
      2. Build context from static KB
      3. Call Gemini with 30s timeout
      4. Parse and return structured JSON
    """
    global _llm, _engine_loaded

    if not _engine_loaded:
        load_schemes_engine()
    if _llm is None:
        load_schemes_engine()

    language = language if language in ("en", "hi", "te") else "en"

    # Build context from static KB
    context = _static_context(question, state, language)
    enriched_q = question
    if state:
        enriched_q += f"\n[Farmer's state: {state}]"

    prompt = _get_prompt(language, context, enriched_q)

    # Call Gemini with timeout protection
    import google.generativeai as genai
    import signal

    def _timeout_handler(signum, frame):
        raise TimeoutError("Gemini API call timed out after 25 seconds")

    raw = ""
    try:
        # Use signal-based timeout on Linux (Render runs Linux)
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(25)  # 25 second timeout
        try:
            response = _llm.generate_content(prompt)
            raw = response.text.strip()
        finally:
            signal.alarm(0)  # Cancel alarm
    except TimeoutError:
        logger.error("[Schemes RAG] Gemini timed out after 25s")
        raise Exception("The AI took too long to respond. Please try again.")
    except Exception as e:
        err = str(e)
        if "RESOURCE_EXHAUSTED" in err or "429" in err or "quota" in err.lower():
            raise Exception("RESOURCE_EXHAUSTED: Gemini API quota exceeded. Please try again later.")
        raise

    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)
    raw = raw.strip()

    # Parse JSON
    result = json.loads(raw)

    result["_meta"] = {
        "vector_db"      : _vector_db,
        "pdf_chunks_used": 0,
        "static_hits"    : len(_static_context(question, state, language).split("---")),
        "llm_model"      : LLM_MODEL,
        "language"       : language,
        "state"          : state or "general",
    }

    return result