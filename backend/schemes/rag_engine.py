# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/rag_engine.py
#
# LangChain RetrievalQA pipeline:
#   ┌─────────────────────────────────────────────────────────────┐
#   │  Query                                                       │
#   │    │                                                         │
#   │    ├─→ FAISS retriever  (primary — loaded from disk)         │
#   │    │       └─ if FAISS unavailable ─→ ChromaDB fallback      │
#   │    │                                                         │
#   │    ├─→ Static KB keyword search  (always runs as supplement) │
#   │    │                                                         │
#   │    └─→ LangChain RetrievalQA chain (Gemini 1.5 Flash LLM)   │
#   │            → answer + source_documents with highlighting     │
#   └─────────────────────────────────────────────────────────────┘
#
# Language support: Hindi (hi) and English (en)
# State focus: Telangana, Andhra Pradesh + all central schemes
#
# Public API:
#   load_schemes_engine()                   → call once at startup
#   ask(question, state, language)          → returns structured dict
# =============================================================================

import os
import re
import json
import textwrap
from pathlib import Path

from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain_google_genai import ChatGoogleGenerativeAI

from schemes.static_kb import search_static, SCHEMES_KB

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
FAISS_DIR  = BASE_DIR / "data" / "scheme_faiss"
CHROMA_DIR = BASE_DIR / "data" / "scheme_chroma"

EMBED_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL   = "gemini-2.5-flash"
TOP_K       = 5

# ── Singletons ────────────────────────────────────────────────────────────────
_retriever   = None   # LangChain BaseRetriever (FAISS or ChromaDB)
_embeddings  = None   # HuggingFaceEmbeddings
_llm         = None   # ChatGoogleGenerativeAI
_vector_db   = "none" # "faiss" | "chroma" | "none"


# =============================================================================
# PROMPT TEMPLATES  (English + Hindi)
# =============================================================================
_PROMPT_EN = PromptTemplate(
    input_variables=["context", "question"],
    template=textwrap.dedent("""
    You are AgriGPT's Government Schemes Assistant helping Indian farmers in
    Telangana and Andhra Pradesh understand government subsidies, insurance,
    seeds, credit, and irrigation schemes.

    ─── RETRIEVED DOCUMENT CONTEXT ──────────────────────────────────────────
    {context}
    ─────────────────────────────────────────────────────────────────────────

    FARMER'S QUESTION: {question}

    INSTRUCTIONS:
    1. Use the retrieved context as primary source. Do NOT invent scheme names or amounts.
    2. Give state-specific details for Telangana (Rythu Bandhu, RSK) and AP (Rythu Bharosa, RBKS).
    3. Always include: eligibility, how to apply, documents needed, helpline.
    4. Keep language simple — farmer-friendly, not bureaucratic.
    5. Respond ONLY with a valid JSON object. No markdown fences, no text outside JSON.

    JSON SCHEMA:
    {{
      "answer": "<clear 3–5 sentence answer>",
      "scheme_name": "<primary scheme name>",
      "eligibility": "<who qualifies>",
      "how_to_apply": "<step-by-step>",
      "documents_needed": ["<doc1>", "<doc2>"],
      "helpline": "<number or URL>",
      "amount_or_benefit": "<₹ amount or subsidy %>",
      "state_specific": "<Telangana or AP specific note, or 'Applies across India'>",
      "sources": ["<source 1>", "<source 2>"],
      "tip": "<one quick action tip for the farmer>"
    }}
    """).strip(),
)

_PROMPT_HI = PromptTemplate(
    input_variables=["context", "question"],
    template=textwrap.dedent("""
    आप AgriGPT के सरकारी योजना सहायक हैं जो तेलंगाना और आंध्र प्रदेश के
    किसानों को सरकारी सब्सिडी, बीमा, बीज, ऋण और सिंचाई योजनाओं के बारे
    में सरल हिंदी में बताते हैं।

    ─── दस्तावेज़ संदर्भ ────────────────────────────────────────────────────
    {context}
    ─────────────────────────────────────────────────────────────────────────

    किसान का प्रश्न: {question}

    निर्देश:
    1. प्राथमिक स्रोत के रूप में संदर्भ का उपयोग करें। योजना नाम या राशि न बनाएं।
    2. तेलंगाना (रायतु बंधु, RSK) और AP (रायतु भरोसा, RBKS) की जानकारी दें।
    3. पात्रता, आवेदन, दस्तावेज़ और हेल्पलाइन जरूर शामिल करें।
    4. सरल किसान-अनुकूल हिंदी में जवाब दें।
    5. केवल एक valid JSON object दें। कोई markdown नहीं, JSON के बाहर कोई text नहीं।

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
      "sources": ["<स्रोत 1>", "<स्रोत 2>"],
      "tip": "<किसान के लिए एक त्वरित सुझाव>"
    }}
    """).strip(),
)

_PROMPT_TE = PromptTemplate(
    input_variables=["context", "question"],
    template=textwrap.dedent("""
    మీరు తెలంగాణ మరియు ఆంధ్రప్రదేశ్ రైతులకు ప్రభుత్వ సబ్సిడీలు, పంటల బీమా, 
    విత్తనాలు, వ్యవసాయ రుణాలు మరియు సాగునీటి పథకాల గురించి స్పష్టమైన తెలుగులో 
    సహాయం చేసే AgriGPT ప్రభుత్వ పథకాల సహాయకులు.

    ─── డాక్యుమెంట్ సమాచారం ───────────────────────────────────────────────────
    {context}
    ─────────────────────────────────────────────────────────────────────────

    రైతు ప్రశ్న: {question}

    సూచనలు:
    1. పొందిన సమాచారాన్ని (Context) మాత్రమే ప్రాథమిక వనరుగా ఉపయోగించండి. స్వంతంగా వివరాలను సృష్టించవద్దు.
    2. తెలంగాణ (రైతు బంధు, RSK) మరియు ఆంధ్రప్రదేశ్ (వైఎస్ఆర్ రైతు భరోసా, RBK) పథకాలకు సంబంధించిన ప్రత్యేక వివరాలను అందించండి.
    3. అర్హత, దరఖాస్తు విధానం, అవసరమైన పత్రాలు మరియు హెల్ప్‌లైన్ నంబర్ తప్పనిసరిగా చేర్చండి.
    4. సాధారణ రైతులకు సులభంగా అర్థమయ్యే సరళమైన తెలుగు భాషలో సమాధానం ఇవ్వండి.
    5. సమాధానాన్ని కేవలం కింది JSON ఫార్మాట్‌లో మాత్రమే ఇవ్వండి. ఎటువంటి మార్క్‌డౌన్ (Markdown) లేదా అదనపు టెక్స్ట్ రాయకూడదు.

    JSON SCHEMA:
    {{
      "answer": "<3-5 వాక్యాలలో స్పష్టమైన సమాధానం>",
      "scheme_name": "<పథకం పేరు>",
      "eligibility": "<ఎవరు అర్హులు>",
      "how_to_apply": "<దరఖాస్తు చేసుకునే విధానం (స్టెప్-బై-స్టెప్)>",
      "documents_needed": ["<కావలసిన పత్రం 1>", "<కావలసిన పత్రం 2>"],
      "helpline": "<హెల్ప్‌లైన్ నంబర్ లేదా వెబ్‌సైట్>",
      "amount_or_benefit": "<సహాయం మొత్తం/సబ్సిడీ శాతం>",
      "state_specific": "<తెలంగాణ లేదా ఏపీ ప్రత్యేక సమాచారం>",
      "sources": ["<వనరు 1>", "<వనరు 2>"],
      "tip": "<రైతుకు ఒక చిన్న సూచన>"
    }}
    """).strip(),
)


# =============================================================================
# STARTUP — load everything once
# =============================================================================
def load_schemes_engine():
    global _retriever, _embeddings, _llm, _vector_db

    # 1. Embeddings ────────────────────────────────────────────────────────────
    print("[Schemes RAG] Loading HuggingFace embeddings...")
    _embeddings = HuggingFaceEmbeddings(
        model_name    = EMBED_MODEL,
        model_kwargs  = {"device": "cpu"},
        encode_kwargs = {"normalize_embeddings": True},
    )
    print(f"[Schemes RAG] Embeddings ready: {EMBED_MODEL}")

    # 2. FAISS (primary) ───────────────────────────────────────────────────────
    faiss_index = FAISS_DIR / "index.faiss"
    if faiss_index.exists():
        try:
            store      = FAISS.load_local(
                str(FAISS_DIR),
                _embeddings,
                allow_dangerous_deserialization=True,
            )
            _retriever = store.as_retriever(search_kwargs={"k": TOP_K})
            _vector_db = "faiss"
            print(f"[Schemes RAG] OK: FAISS loaded from {FAISS_DIR}")
        except Exception as e:
            print(f"[Schemes RAG] [WARNING] FAISS load failed: {e} - trying ChromaDB...")

    # 3. ChromaDB fallback ─────────────────────────────────────────────────────
    if _retriever is None:
        chroma_db = CHROMA_DIR / "chroma.sqlite3"
        if chroma_db.exists():
            try:
                store      = Chroma(
                    persist_directory = str(CHROMA_DIR),
                    embedding_function = _embeddings,
                    collection_name    = "scheme_docs",
                )
                _retriever = store.as_retriever(search_kwargs={"k": TOP_K})
                _vector_db = "chroma"
                print(f"[Schemes RAG] OK: ChromaDB loaded from {CHROMA_DIR}")
            except Exception as e:
                print(f"[Schemes RAG] [WARNING] ChromaDB load failed: {e}")

    if _retriever is None:
        print(
            "[Schemes RAG] [WARNING] No vector DB found. "
            "Run  python -m schemes.ingest  after placing PDFs in data/scheme_pdfs/. "
            "Static KB only mode active."
        )
        _vector_db = "none"

    # 4. LLM — Gemini via LangChain ────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set.\n"
            "Get free key: https://aistudio.google.com/app/apikey\n"
            "Then: set GEMINI_API_KEY=your-key"
        )
    _llm = ChatGoogleGenerativeAI(
        model       = LLM_MODEL,
        google_api_key = api_key,
        temperature = 0.1,   # low temp for factual grounded answers
        convert_system_message_to_human=True,
    )
    print(f"[Schemes RAG] Gemini LLM ready: {LLM_MODEL} (via LangChain)")


# =============================================================================
# BUILD RETRIEVAL QA CHAIN
# =============================================================================
def _build_chain(language: str) -> RetrievalQA | None:
    """Build LangChain RetrievalQA chain with source document return."""
    if _retriever is None:
        return None

    if language == "hi":
        prompt = _PROMPT_HI
    elif language == "te":
        prompt = _PROMPT_TE
    else:
        prompt = _PROMPT_EN

    chain = RetrievalQA.from_chain_type(
        llm                  = _llm,
        chain_type           = "stuff",        # stuff all chunks into one prompt
        retriever            = _retriever,
        return_source_documents = True,         # ← source highlighting
        chain_type_kwargs    = {
            "prompt"         : prompt,
            "document_separator": "\n\n---\n\n",
        },
    )
    return chain


# =============================================================================
# SOURCE HIGHLIGHT EXTRACTOR
# =============================================================================
def _extract_sources(source_docs: list) -> list[dict]:
    """
    Extract source metadata from LangChain source_documents for citation display.
    Returns list of {file, page, snippet} dicts.
    """
    seen    = set()
    sources = []
    for doc in source_docs:
        meta    = doc.metadata or {}
        file    = meta.get("source", "Unknown PDF")
        page    = meta.get("page", "?")
        snippet = doc.page_content[:200].strip().replace("\n", " ")
        key     = f"{file}:{page}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "file"   : Path(file).name if file != "Unknown PDF" else file,
                "page"   : page,
                "snippet": snippet,
            })
    return sources


# =============================================================================
# STATIC KB CONTEXT BUILDER
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
        parts.append(f"[{e['name']} | {e['type']}]\n{content.strip()}\nSource: {e['source']}")
    return "\n\n---\n\n".join(parts)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def ask(
    question : str,
    state    : str = "",
    language : str = "en",   # "en" or "hi"
) -> dict:
    """
    LangChain RetrievalQA pipeline for Government Schemes Q&A.

    Flow:
      1. If FAISS/ChromaDB available → RetrievalQA chain with source documents
      2. Static KB always supplements as additional context
      3. Gemini generates structured JSON answer
      4. Sources extracted and highlighted from retrieved documents

    Returns:
      dict with answer, eligibility, how_to_apply, documents_needed,
      helpline, amount_or_benefit, sources (with page + snippet), state_specific, tip, _meta
    """
    language = language if language in ("en", "hi", "te") else "en"

    # ── 1. Build RetrievalQA chain ────────────────────────────────────────────
    chain = _build_chain(language)

    # ── 2. Static KB supplement ───────────────────────────────────────────────
    static_ctx = _static_context(question, state, language)

    # ── 3a. Run LangChain chain (if vector DB available) ──────────────────────
    source_docs     = []
    raw_llm_answer  = ""
    used_vector_db  = False

    if chain is not None:
        enriched_q = (
            f"{question}\n\n"
            f"[Farmer State: {state or 'Not specified'}]\n\n"
            f"[Additional verified context]\n{static_ctx}"
        )
        result          = chain.invoke({"query": enriched_q})
        raw_llm_answer  = result.get("result", "")
        source_docs     = result.get("source_documents", [])
        used_vector_db  = True

    # ── 3b. Static KB only fallback (no vector DB) ────────────────────────────
    else:
        if language == "hi":
            prompt_cls = _PROMPT_HI
        elif language == "te":
            prompt_cls = _PROMPT_TE
        else:
            prompt_cls = _PROMPT_EN
        filled      = prompt_cls.format(
            context  = static_ctx,
            question = f"{question}\n[State: {state or 'Not specified'}]",
        )
        response        = _llm.invoke(filled)
        raw_llm_answer  = response.content

    # ── 4. Strip markdown fences & parse JSON ─────────────────────────────────
    raw = raw_llm_answer.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)
    raw = raw.strip()

    result_dict = json.loads(raw)

    # ── 5. Attach source highlights ───────────────────────────────────────────
    result_dict["source_highlights"] = _extract_sources(source_docs)

    # ── 6. Metadata ───────────────────────────────────────────────────────────
    result_dict["_meta"] = {
        "vector_db"       : _vector_db,
        "used_vector_db"  : used_vector_db,
        "pdf_chunks_used" : len(source_docs),
        "llm_model"       : LLM_MODEL,
        "language"        : language,
        "state"           : state or "general",
    }

    return result_dict
