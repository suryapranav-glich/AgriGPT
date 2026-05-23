# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/rag_engine.py  (Fixed for Render free tier)
#
# KEY FIXES:
#   1. HuggingFaceEmbeddings only loaded when FAISS/ChromaDB index exists
#   2. Removed invalid 'langchain_classic' import (doesn't exist)
#   3. Falls back to static KB + Gemini directly when no vector DB
#   4. Engine loaded only once (_engine_loaded flag)
# =============================================================================

import os
import re
import json
import textwrap
from pathlib import Path

import google.generativeai as genai

from schemes.static_kb import search_static

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
FAISS_DIR  = BASE_DIR / "data" / "scheme_faiss"
CHROMA_DIR = BASE_DIR / "data" / "scheme_chroma"

EMBED_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL   = "gemini-2.5-flash"
TOP_K       = 5

# ── Singletons ────────────────────────────────────────────────────────────────
_retriever     = None
_embeddings    = None
_llm           = None
_vector_db     = "none"
_engine_loaded = False


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================
def _get_prompt(language: str, context: str, question: str) -> str:
    if language == "hi":
        return textwrap.dedent(f"""
        आप AgriGPT के सरकारी योजना सहायक हैं जो तेलंगाना और आंध्र प्रदेश के
        किसानों को सरकारी सब्सिडी, बीमा, बीज, ऋण और सिंचाई योजनाओं के बारे
        में सरल हिंदी में बताते हैं।

        ─── संदर्भ ──────────────────────────────────────────────────────────
        {context}
        ─────────────────────────────────────────────────────────────────────

        किसान का प्रश्न: {question}

        निर्देश:
        1. संदर्भ का उपयोग करें। योजना नाम या राशि न बनाएं।
        2. पात्रता, आवेदन, दस्तावेज़ और हेल्पलाइन जरूर शामिल करें।
        3. सरल हिंदी में जवाब दें।
        4. केवल एक valid JSON object दें। कोई markdown नहीं।

        JSON SCHEMA:
        {{
          "answer": "<3-5 वाक्यों में स्पष्ट उत्तर>",
          "scheme_name": "<मुख्य योजना का नाम>",
          "eligibility": "<कौन पात्र है>",
          "how_to_apply": "<चरण-दर-चरण>",
          "documents_needed": ["<दस्तावेज़ 1>", "<दस्तावेज़ 2>"],
          "helpline": "<नंबर या URL>",
          "amount_or_benefit": "<₹ राशि या सब्सिडी %>",
          "state_specific": "<तेलंगाना या AP की विशेष जानकारी>",
          "sources": ["<स्रोत 1>"],
          "tip": "<किसान के लिए एक त्वरित सुझाव>"
        }}
        """).strip()

    elif language == "te":
        return textwrap.dedent(f"""
        మీరు తెలంగాణ మరియు ఆంధ్రప్రదేశ్ రైతులకు ప్రభుత్వ పథకాల గురించి
        స్పష్టమైన తెలుగులో సహాయం చేసే AgriGPT సహాయకులు.

        ─── సమాచారం ─────────────────────────────────────────────────────────
        {context}
        ─────────────────────────────────────────────────────────────────────

        రైతు ప్రశ్న: {question}

        సూచనలు:
        1. పొందిన సమాచారాన్ని మాత్రమే ఉపయోగించండి.
        2. అర్హత, దరఖాస్తు విధానం, పత్రాలు మరియు హెల్ప్‌లైన్ చేర్చండి.
        3. సరళమైన తెలుగులో సమాధానం ఇవ్వండి.
        4. కేవలం JSON మాత్రమే ఇవ్వండి. Markdown వద్దు.

        JSON SCHEMA:
        {{
          "answer": "<3-5 వాక్యాలలో స్పష్టమైన సమాధానం>",
          "scheme_name": "<పథకం పేరు>",
          "eligibility": "<ఎవరు అర్హులు>",
          "how_to_apply": "<దరఖాస్తు విధానం>",
          "documents_needed": ["<పత్రం 1>", "<పత్రం 2>"],
          "helpline": "<హెల్ప్‌లైన్ నంబర్>",
          "amount_or_benefit": "<సహాయం మొత్తం>",
          "state_specific": "<తెలంగాణ లేదా ఏపీ సమాచారం>",
          "sources": ["<వనరు 1>"],
          "tip": "<రైతుకు ఒక సూచన>"
        }}
        """).strip()

    else:  # English (default)
        return textwrap.dedent(f"""
        You are AgriGPT's Government Schemes Assistant helping Indian farmers
        understand government subsidies, insurance, seeds, credit, and irrigation schemes.
        Focus on Telangana and Andhra Pradesh schemes.

        ─── CONTEXT ──────────────────────────────────────────────────────────
        {context}
        ─────────────────────────────────────────────────────────────────────

        FARMER'S QUESTION: {question}

        INSTRUCTIONS:
        1. Use ONLY the context above. Do NOT invent scheme names or amounts.
        2. Give state-specific details for Telangana (Rythu Bandhu, RSK) and AP (Rythu Bharosa, RBKS).
        3. Always include: eligibility, how to apply, documents needed, helpline.
        4. Keep language simple and farmer-friendly.
        5. Respond ONLY with a valid JSON object. No markdown fences.

        JSON SCHEMA:
        {{
          "answer": "<clear 3-5 sentence answer>",
          "scheme_name": "<primary scheme name>",
          "eligibility": "<who qualifies>",
          "how_to_apply": "<step-by-step process>",
          "documents_needed": ["<doc1>", "<doc2>"],
          "helpline": "<number or URL>",
          "amount_or_benefit": "<₹ amount or subsidy %>",
          "state_specific": "<Telangana or AP specific note, or 'Applies across India'>",
          "sources": ["<source 1>"],
          "tip": "<one quick action tip for the farmer>"
        }}
        """).strip()


# =============================================================================
# STARTUP
# =============================================================================
def load_schemes_engine():
    """
    Initialise Gemini always.
    Only load embedder + vector DB if index files exist on disk.
    This prevents OOM crash on Render free tier.
    """
    global _retriever, _embeddings, _llm, _vector_db, _engine_loaded

    if _engine_loaded:
        return

    faiss_index  = FAISS_DIR  / "index.faiss"
    chroma_db    = CHROMA_DIR / "chroma.sqlite3"
    index_exists = faiss_index.exists() or chroma_db.exists()

    # 1. Embedder + Vector DB — ONLY if index exists ───────────────────────────
    if index_exists:
        print("[Schemes RAG] Vector index found — loading embedder...")
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            _embeddings = HuggingFaceEmbeddings(
                model_name    = EMBED_MODEL,
                model_kwargs  = {"device": "cpu"},
                encode_kwargs = {"normalize_embeddings": True},
            )
            print(f"[Schemes RAG] Embeddings ready: {EMBED_MODEL}")

            # Try FAISS first
            if faiss_index.exists():
                try:
                    from langchain_community.vectorstores import FAISS
                    store      = FAISS.load_local(
                        str(FAISS_DIR),
                        _embeddings,
                        allow_dangerous_deserialization=True,
                    )
                    _retriever = store.as_retriever(search_kwargs={"k": TOP_K})
                    _vector_db = "faiss"
                    print(f"[Schemes RAG] FAISS loaded from {FAISS_DIR}")
                except Exception as e:
                    print(f"[Schemes RAG] FAISS load failed: {e}")

            # ChromaDB fallback
            if _retriever is None and chroma_db.exists():
                try:
                    from langchain_community.vectorstores import Chroma
                    store      = Chroma(
                        persist_directory  = str(CHROMA_DIR),
                        embedding_function = _embeddings,
                        collection_name    = "scheme_docs",
                    )
                    _retriever = store.as_retriever(search_kwargs={"k": TOP_K})
                    _vector_db = "chroma"
                    print(f"[Schemes RAG] ChromaDB loaded from {CHROMA_DIR}")
                except Exception as e:
                    print(f"[Schemes RAG] ChromaDB load failed: {e}")

        except Exception as e:
            print(f"[Schemes RAG] WARNING: Embedder load failed: {e}. Using static KB only.")
            _embeddings = None
            _retriever  = None
            _vector_db  = "none"
    else:
        print(
            "[Schemes RAG] No vector index found — skipping embedder.\n"
            "  Using static knowledge base + Gemini directly.\n"
            "  To enable PDF retrieval: run  python -m schemes.ingest"
        )
        _vector_db = "none"

    # 2. Gemini client — always initialised ───────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Add it in your Render Environment Variables dashboard."
        )
    genai.configure(api_key=api_key)
    _llm = genai.GenerativeModel(LLM_MODEL)
    print(f"[Schemes RAG] Gemini ready — model: {LLM_MODEL}")

    _engine_loaded = True


# =============================================================================
# RETRIEVAL (vector DB)
# =============================================================================
def _vector_retrieve(query: str) -> str:
    """Returns formatted context string from vector DB, or empty string."""
    if _retriever is None:
        return ""
    try:
        docs = _retriever.invoke(query)
        if not docs:
            return ""
        parts = []
        for doc in docs:
            src = doc.metadata.get("source", "Unknown")
            parts.append(f"[Source: {src}]\n{doc.page_content.strip()}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        print(f"[Schemes RAG] Vector retrieval error: {e}")
        return ""


# =============================================================================
# STATIC KB CONTEXT
# =============================================================================
def _static_context(question: str, state: str, language: str) -> str:
    hits = search_static(question, state=state, top_k=3)
    if not hits:
        return "No matching static KB entries."
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
    Schemes Q&A pipeline:
      1. Ensure engine loaded (Gemini always; vector DB only if index exists)
      2. Retrieve context: vector DB (if available) + static KB (always)
      3. Call Gemini with combined context
      4. Parse and return structured JSON
    """
    global _llm

    if not _engine_loaded:
        load_schemes_engine()
    if _llm is None:
        load_schemes_engine()

    language = language if language in ("en", "hi", "te") else "en"

    # 1. Build context ─────────────────────────────────────────────────────────
    static_ctx = _static_context(question, state, language)
    vector_ctx = _vector_retrieve(
        f"{question} {state} farmer scheme eligibility apply"
    )

    combined_context = ""
    if vector_ctx:
        combined_context += f"=== RETRIEVED PDF CONTEXT ===\n{vector_ctx}\n\n"
    combined_context += f"=== VERIFIED STATIC KNOWLEDGE BASE ===\n{static_ctx}"

    # 2. Add state to question for better targeting ────────────────────────────
    enriched_q = question
    if state:
        enriched_q += f"\n[Farmer's state: {state}]"

    # 3. Build prompt and call Gemini ──────────────────────────────────────────
    prompt   = _get_prompt(language, combined_context, enriched_q)
    response = _llm.generate_content(prompt)
    raw      = response.text.strip()

    # 4. Strip markdown fences ─────────────────────────────────────────────────
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)
    raw = raw.strip()

    # 5. Parse JSON ────────────────────────────────────────────────────────────
    result = json.loads(raw)

    # 6. Metadata ──────────────────────────────────────────────────────────────
    result["_meta"] = {
        "vector_db"      : _vector_db,
        "pdf_chunks_used": 1 if vector_ctx else 0,
        "static_hits"    : len(search_static(question, state=state, top_k=3)),
        "llm_model"      : LLM_MODEL,
        "language"       : language,
        "state"          : state or "general",
    }

    return result