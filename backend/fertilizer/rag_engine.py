# =============================================================================
# AgriGPT — Feature 3: Fertilizer Recommendation Engine
# fertilizer/rag_engine.py  (Gemini version — free tier)
#
# Loaded once at FastAPI startup.
# Public API:
#   load_rag_engine()                                  → call at startup
#   recommend(crop, soil_type, growth_stage, symptoms) → returns dict
# =============================================================================

import os
import re
import json
import textwrap
import numpy as np
from pathlib import Path

import faiss
import google.generativeai as genai
from sentence_transformers import SentenceTransformer

from fertilizer.static_kb import lookup as static_lookup

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
INDEX_PATH  = BASE_DIR / "data" / "faiss_index" / "icar.index"
CHUNKS_PATH = BASE_DIR / "data" / "faiss_index" / "chunks.json"

EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K       = 6

# Gemini model — gemini-2.5-flash is free tier (matches blueprint)
LLM_MODEL   = "gemini-2.5-flash"

# ── Module-level singletons ───────────────────────────────────────────────────
_index    = None
_chunks   = None
_embedder = None
_llm      = None   # google.generativeai.GenerativeModel instance


# =============================================================================
# STARTUP
# =============================================================================
def load_rag_engine():
    """
    Call ONCE at FastAPI startup.
    Initialises embedder, FAISS index, and Gemini client.
    """
    global _index, _chunks, _embedder, _llm

    # 1. Sentence-transformer embedder ────────────────────────────────────────
    print("[Fertilizer RAG] Loading embedder …")
    _embedder = SentenceTransformer(EMBED_MODEL)
    print(f"[Fertilizer RAG] Embedder ready: {EMBED_MODEL}")

    # 2. FAISS index (optional) ───────────────────────────────────────────────
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        _index = faiss.read_index(str(INDEX_PATH))
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            _chunks = json.load(f)
        print(f"[Fertilizer RAG] FAISS index: {_index.ntotal} vectors, {len(_chunks)} chunks")
    else:
        print(
            "[Fertilizer RAG] [WARNING] No FAISS index found. "
            "Run  python -m fertilizer.ingest  after placing ICAR PDFs in data/icar_pdfs/. "
            "Static knowledge base will be used as context."
        )
        _index  = None
        _chunks = None

    # 3. Gemini client ────────────────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set.\n"
            "Get a free key at: https://aistudio.google.com/app/apikey\n"
            "Then run:  set GEMINI_API_KEY=your-key-here  (Windows PowerShell)"
        )
    genai.configure(api_key=api_key)
    _llm = genai.GenerativeModel(LLM_MODEL)
    print(f"[Fertilizer RAG] Gemini client ready — model: {LLM_MODEL}")


# =============================================================================
# RETRIEVAL
# =============================================================================
def _retrieve(query: str, k: int = TOP_K) -> list[dict]:
    if _index is None or _chunks is None:
        return []
    vec = _embedder.encode([query], normalize_embeddings=True).astype(np.float32)
    scores, idxs = _index.search(vec, k)
    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0:
            continue
        chunk = dict(_chunks[idx])
        chunk["retrieval_score"] = round(float(score), 4)
        results.append(chunk)
    return results


# =============================================================================
# PROMPT BUILDER
# =============================================================================
def _build_prompt(
    crop: str,
    soil_type: str,
    growth_stage: str,
    symptoms: str,
    icar_context: str,
    static_context: str,
) -> str:
    symptom_line = symptoms.strip() if symptoms.strip() else "None reported"

    return textwrap.dedent(f"""
    You are AgriGPT's senior agronomist following ICAR (Indian Council of Agricultural Research)
    guidelines for Indian farming conditions. Give a precise, correct, actionable fertilizer
    recommendation.

    ─── ICAR PDF CONTEXT (retrieved) ───────────────────────────────────────────
    {icar_context}
    ─────────────────────────────────────────────────────────────────────────────

    ─── STATIC ICAR KNOWLEDGE BASE (verified baseline) ──────────────────────────
    {static_context}
    ─────────────────────────────────────────────────────────────────────────────

    FARMER QUERY
    - Crop            : {crop}
    - Soil Type       : {soil_type}
    - Growth Stage    : {growth_stage}
    - Visible Symptoms: {symptom_line}

    INSTRUCTIONS
    1. Use ICAR PDF context first. Fall back to static KB. Do NOT invent values.
    2. Adjust NPK doses for soil type:
       - Sandy / light soils   → reduce each dose by 10%, prefer split applications
       - Clay / heavy soils    → standard dose; reduce K by 10%
       - Red laterite soils    → add 20% K; ensure Zn and B micronutrients
       - Black cotton (Vertisol) → standard N; increase P by 10%
    3. If deficiency symptoms are given, add targeted treatment in "deficiency_treatment".
    4. All quantities must be in kg/acre unless stated otherwise.
    5. Respond ONLY with a single valid JSON object.
       Do NOT include markdown code fences (no ```json), no explanation outside the JSON.

    JSON SCHEMA (follow exactly):
    {{
      "crop": "{crop}",
      "soil_type": "{soil_type}",
      "growth_stage": "{growth_stage}",
      "npk_summary": "N:P:K = X:Y:Z kg/acre (total season)",
      "fertilizer_schedule": [
        {{
          "timing": "<e.g. Basal at sowing>",
          "dap_days": <integer days after planting/sowing/transplanting>,
          "fertilizers": [
            {{
              "name": "<fertilizer name e.g. Urea, DAP, MOP>",
              "dose_kg_per_acre": <number>,
              "nutrient_supplied": "<brief description>"
            }}
          ],
          "notes": "<practical application note>"
        }}
      ],
      "organic_alternatives": [
        {{
          "name": "<organic input name>",
          "dose_kg_per_acre": <number or null>,
          "timing": "<when to apply>",
          "benefit": "<key benefit>"
        }}
      ],
      "deficiency_treatment": "<targeted treatment if symptoms given, else 'No specific deficiency reported.'>",
      "micronutrients": "<zinc, boron, iron etc. recommendations if relevant>",
      "cautions": "<key warnings for this crop and stage>",
      "icar_source": "<ICAR document name from context, or 'ICAR General Nutrient Management Guidelines'>"
    }}
    """).strip()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def recommend(
    crop: str,
    soil_type: str,
    growth_stage: str,
    symptoms: str = "",
) -> dict:
    """
    Full RAG pipeline:
      1. Build query → retrieve ICAR PDF chunks from FAISS
      2. Pull verified static KB entry as baseline
      3. Call Gemini with both context sources
      4. Parse and return structured JSON

    Raises:
        json.JSONDecodeError — if Gemini returns malformed JSON
        Exception            — on API / network errors
    """
    # 1. Query ─────────────────────────────────────────────────────────────────
    query = (
        f"{crop} {soil_type} fertilizer NPK recommendation "
        f"{growth_stage} stage {symptoms}"
    )

    # 2. FAISS retrieval ───────────────────────────────────────────────────────
    retrieved    = _retrieve(query)
    icar_context = (
        "\n\n".join(
            f"[Source: {c['source']} | score: {c['retrieval_score']}]\n{c['text']}"
            for c in retrieved
        )
        if retrieved
        else "No PDF context available. Use static knowledge base."
    )

    # 3. Static KB ─────────────────────────────────────────────────────────────
    static_entry   = static_lookup(crop)
    static_context = (
        json.dumps(static_entry, indent=2)
        if static_entry
        else f"No static entry for '{crop}'. Use ICAR PDF context and standard guidelines."
    )

    # 4. Gemini call ───────────────────────────────────────────────────────────
    prompt   = _build_prompt(crop, soil_type, growth_stage, symptoms,
                             icar_context, static_context)
    response = _llm.generate_content(prompt)
    raw      = response.text.strip()

    # 5. Strip accidental markdown fences ─────────────────────────────────────
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)
    raw = raw.strip()

    # 6. Parse JSON ────────────────────────────────────────────────────────────
    result = json.loads(raw)

    # 7. Attach retrieval metadata ─────────────────────────────────────────────
    result["_meta"] = {
        "retrieved_sources": list({c["source"] for c in retrieved}),
        "rag_chunks_used"  : len(retrieved),
        "used_static_kb"   : static_entry is not None,
        "llm_model"        : LLM_MODEL,
    }

    return result
