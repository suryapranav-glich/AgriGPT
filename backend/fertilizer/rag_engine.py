# =============================================================================
# AgriGPT — Feature 3: Fertilizer Recommendation Engine
# fertilizer/rag_engine.py  (Fixed for Render free tier)
#
# KEY FIX: Embedder is only loaded when FAISS index exists.
# Without ICAR PDFs ingested, we skip sentence_transformers entirely
# and go straight to Gemini with the static knowledge base.
# =============================================================================

import os
import re
import json
import textwrap
import numpy as np
from pathlib import Path

import google.generativeai as genai

from fertilizer.static_kb import lookup as static_lookup

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
INDEX_PATH  = BASE_DIR / "data" / "faiss_index" / "icar.index"
CHUNKS_PATH = BASE_DIR / "data" / "faiss_index" / "chunks.json"

EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K       = 6

LLM_MODEL   = "gemini-2.5-flash"

# ── Module-level singletons ───────────────────────────────────────────────────
_index    = None
_chunks   = None
_embedder = None
_llm      = None
_engine_loaded = False


# =============================================================================
# STARTUP
# =============================================================================
def load_rag_engine():
    """
    Call ONCE at FastAPI startup.
    Initialises Gemini client always.
    Only loads FAISS + embedder if index files exist (i.e. PDFs were ingested).
    """
    global _index, _chunks, _embedder, _llm, _engine_loaded

    if _engine_loaded:
        return

    # 1. FAISS index (OPTIONAL — only load if index exists) ───────────────────
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        print("[Fertilizer RAG] FAISS index found — loading embedder …")
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            _embedder = SentenceTransformer(EMBED_MODEL)
            _index    = faiss.read_index(str(INDEX_PATH))
            with open(CHUNKS_PATH, encoding="utf-8") as f:
                _chunks = json.load(f)
            print(f"[Fertilizer RAG] FAISS ready: {_index.ntotal} vectors, {len(_chunks)} chunks")
        except Exception as e:
            print(f"[Fertilizer RAG] WARNING: Could not load FAISS index: {e}")
            _index    = None
            _chunks   = None
            _embedder = None
    else:
        print(
            "[Fertilizer RAG] No FAISS index found — skipping embedder load.\n"
            "  Static knowledge base will be used as context.\n"
            "  To enable PDF retrieval: place ICAR PDFs in data/icar_pdfs/ and run:\n"
            "    python -m fertilizer.ingest"
        )
        _index    = None
        _chunks   = None
        _embedder = None

    # 2. Gemini client ────────────────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Set it in your Render environment variables dashboard."
        )
    genai.configure(api_key=api_key)
    _llm = genai.GenerativeModel(LLM_MODEL)
    print(f"[Fertilizer RAG] Gemini client ready — model: {LLM_MODEL}")

    _engine_loaded = True


# =============================================================================
# RETRIEVAL
# =============================================================================
def _retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Returns FAISS chunks if index is loaded, else empty list."""
    if _index is None or _chunks is None or _embedder is None:
        return []
    try:
        import numpy as np
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
    except Exception as e:
        print(f"[Fertilizer RAG] Retrieval error: {e}")
        return []


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
    RAG pipeline:
      1. Ensure engine is loaded (Gemini always; FAISS only if index exists)
      2. Retrieve ICAR PDF chunks from FAISS (if available)
      3. Pull static KB entry as baseline
      4. Call Gemini with both context sources
      5. Parse and return structured JSON
    """
    global _llm

    # Lazy load on first call
    if not _engine_loaded:
        load_rag_engine()

    # Safety check
    if _llm is None:
        load_rag_engine()

    # 1. Build query ───────────────────────────────────────────────────────────
    query = (
        f"{crop} {soil_type} fertilizer NPK recommendation "
        f"{growth_stage} stage {symptoms}"
    )

    # 2. FAISS retrieval (empty list if no index) ──────────────────────────────
    retrieved    = _retrieve(query)
    icar_context = (
        "\n\n".join(
            f"[Source: {c['source']} | score: {c['retrieval_score']}]\n{c['text']}"
            for c in retrieved
        )
        if retrieved
        else "No PDF context available. Use static knowledge base only."
    )

    # 3. Static KB ─────────────────────────────────────────────────────────────
    static_entry   = static_lookup(crop)
    static_context = (
        json.dumps(static_entry, indent=2)
        if static_entry
        else f"No static entry for '{crop}'. Use ICAR general guidelines."
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
        "faiss_active"     : _index is not None,
    }

    return result