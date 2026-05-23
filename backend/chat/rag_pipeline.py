"""
rag_pipeline.py
───────────────
Lightweight keyword-based retrieval for static KNOWLEDGE_CHUNKS.

WHY NOT FAISS?
  The knowledge base is a small static Python list (~30+ chunks).
  SentenceTransformer + FAISS uses ~250 MB RAM — crashes Render free tier (512 MB).
  Keyword TF-IDF scoring is equally effective for a small fixed corpus and uses < 5 MB.

Changes in this version
  ✅ FIX 3 — retrieve() now accepts an *intent* parameter.
             Chunks whose "agent" category matches the intent get a
             STRONG boost (3×); mismatched categories get a PENALTY (0.3×).
             This means "yield estimation of paddy per acre" returns
             seed/general chunks only — NOT spray/weather/market chunks.

  ✅ FIX 5 — retrieve() now accepts a *crop* parameter.
             When a specific crop is detected (e.g. "paddy"), only
             crop-matching chunks AND crop-agnostic chunks (soil, market,
             disease, weather, scheme) enter the scoring pool.
             This stops groundnut/soybean chunks from polluting a paddy query.

Flow:
  1. farming_agent detects intent via detect_intent(query)
  2. farming_agent detects crop via _extract_crop(query)
  3. Passes both into retrieve(query, intent=intent, crop=crop)
  4. retrieve() pre-filters by crop prefix, then scores with TF-IDF + intent boost
  5. Returns top-K chunks to farming_agent for prompt construction
"""

from __future__ import annotations

import re
import math
import logging
from collections import Counter

from chat.knowledge_base import KNOWLEDGE_CHUNKS
from chat.config import INTENT_TO_CHUNK_CATEGORIES

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CROP → CHUNK ID PREFIX MAP
#
# Maps detected crop names to the chunk id prefix(es) used in knowledge_base.py.
# Chunks whose id starts with a matching prefix are "crop-specific" and stay in
# the scoring pool.  Everything else is filtered OUT unless it's crop-agnostic.
#
# Keep this in sync with _KNOWN_CROPS_ORDERED in farming_agent.py.
# ─────────────────────────────────────────────────────────────────────────────

CROP_TO_ID_PREFIX: dict[str, list[str]] = {
    "paddy":       ["rice_"],
    "rice":        ["rice_"],
    "wheat":       ["wheat_"],          # no wheat chunk yet → market fallback
    "cotton":      ["cotton_"],
    "maize":       ["maize_"],
    "corn":        ["maize_"],
    "soybean":     ["soy_"],
    "groundnut":   ["gnut_"],
    "chilli":      ["hort_"],
    "onion":       ["hort_"],
    "tomato":      ["hort_"],
    "potato":      ["hort_"],
    "brinjal":     ["hort_"],
    "cabbage":     ["hort_"],
    "cauliflower": ["hort_"],
    "banana":      ["hort_"],
    "mango":       ["hort_"],
    # Crops without a dedicated chunk — fall through to agnostic pool only
    "jowar":       [],
    "bajra":       [],
    "ragi":        [],
    "tur":         [],
    "arhar":       [],
    "moong":       [],
    "urad":        [],
    "mustard":     [],
    "sunflower":   [],
    "sugarcane":   [],
}

# These chunk-id prefixes are crop-agnostic and are ALWAYS included in the
# scoring pool, regardless of which crop was detected.
_CROP_AGNOSTIC_PREFIXES: tuple[str, ...] = (
    "soil_",
    "irrigation_",
    "market_",
    "disease_",
    "weather_",
    "scheme_",
    "disease_auto_",
)


# ─────────────────────────────────────────────────────────────────────────────
# TF-IDF CORPUS PRE-COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "the", "a", "an", "is", "in", "of", "to", "and", "or", "for",
    "on", "at", "by", "from", "are", "was", "with", "that", "this",
    "it", "as", "be", "can", "will", "per", "use", "used", "also",
    "have", "has", "not", "no", "if", "its", "than", "each", "all",
}

# Maps our internal intent names to the chunk "agent" field values used in
# knowledge_base.py.  Needed because knowledge_base uses "general"/"disease"/
# "market" while config uses fine-grained intents like "yield"/"fertilizer".
_INTENT_TO_AGENT: dict[str, list[str]] = {
    "weather":    ["general"],
    "disease":    ["disease"],
    "spraying":   ["disease", "general"],
    "fertilizer": ["general"],          # fertilizer chunks are tagged "general"
    "irrigation": ["general"],
    "market":     ["market"],
    "yield":      ["general"],          # yield/variety chunks are tagged "general"
    "soil":       ["general"],
    "seed":       ["general"],
    "scheme":     ["market"],           # scheme chunks are tagged "market"
    "general":    ["general", "disease", "market"],
}

# Scoring multipliers
_INTENT_MATCH_BOOST      = 3.0   # chunk agent matches intent
_INTENT_MISMATCH_PENALTY = 0.3   # chunk agent does NOT match intent
# "general" chunks are always slightly relevant as fallback
_GENERAL_AGENT_FLOOR     = 0.6   # applied to "general" chunks when intent is specific


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r'\b[a-z]{2,}\b', text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _build_idf() -> dict[str, float]:
    n = len(KNOWLEDGE_CHUNKS)
    df: dict[str, int] = {}
    for chunk in KNOWLEDGE_CHUNKS:
        terms = set(_tokenize(chunk["content"] + " " + chunk.get("topic", "")))
        for term in terms:
            df[term] = df.get(term, 0) + 1
    return {term: math.log(n / count + 1) for term, count in df.items()}


# Pre-compute once at module import (< 1 ms, no ML model needed)
_IDF = _build_idf()


# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────

def _score_chunk(
    chunk:         dict,
    query_tokens:  list[str],
    query_counter: Counter,
    intent:        str,
) -> float:
    """
    Score a single chunk against the query using TF-IDF weighted overlap,
    then apply an intent-category boost or penalty.

    Boost logic
    -----------
    • Chunk agent IN the allowed agents for this intent  → ×3.0
    • Chunk agent == "general" and intent is specific    → ×0.6  (soft floor)
    • Chunk agent NOT in allowed agents                  → ×0.3  (penalised)

    This ensures that for a "yield" query:
      - general/seed chunks rise to the top
      - market/disease chunks are effectively buried
    """
    chunk_text    = chunk["content"] + " " + chunk.get("topic", "") + " " + chunk.get("id", "")
    chunk_tokens  = _tokenize(chunk_text)
    chunk_counter = Counter(chunk_tokens)
    chunk_len     = max(len(chunk_tokens), 1)

    # TF-IDF overlap score
    base_score = 0.0
    for term in query_tokens:
        if term in chunk_counter:
            tf  = chunk_counter[term] / chunk_len
            idf = _IDF.get(term, 1.0)
            base_score += tf * idf * query_counter[term]

    if base_score == 0.0:
        return 0.0

    # Intent-based multiplier
    chunk_agent    = chunk.get("agent", "general")
    allowed_agents = _INTENT_TO_AGENT.get(intent, ["general", "disease", "market"])

    if chunk_agent in allowed_agents:
        multiplier = _INTENT_MATCH_BOOST
    elif chunk_agent == "general":
        # General chunks are a safe fallback — don't bury them completely
        multiplier = _GENERAL_AGENT_FLOOR
    else:
        multiplier = _INTENT_MISMATCH_PENALTY

    return base_score * multiplier


# ─────────────────────────────────────────────────────────────────────────────
# CROP PRE-FILTER
# ─────────────────────────────────────────────────────────────────────────────

def _apply_crop_filter(crop: str | None) -> list[dict]:
    """
    Return the subset of KNOWLEDGE_CHUNKS that should be scored for *crop*.

    When crop is detected:
      • Keep chunks whose id starts with a crop-specific prefix (e.g. "rice_")
      • Always keep crop-agnostic chunks (soil, market, disease, weather, scheme)
      • Drop all other crop-specific chunks (e.g. "gnut_", "soy_", "cotton_")

    When crop is None: return the full corpus unchanged.

    This is the key fix for the "paddy yield → groundnut answer" bug:
    before TF-IDF even runs, groundnut/soybean/maize chunks are excluded
    when the farmer asks about paddy.
    """
    if not crop:
        return KNOWLEDGE_CHUNKS

    crop_lower = crop.lower()
    crop_prefixes = CROP_TO_ID_PREFIX.get(crop_lower)

    if crop_prefixes is None:
        # Completely unknown crop — no filter, let TF-IDF sort it out
        logger.debug("Crop filter: unknown crop '%s' — using full corpus", crop)
        return KNOWLEDGE_CHUNKS

    filtered = []
    for chunk in KNOWLEDGE_CHUNKS:
        chunk_id = chunk.get("id", "")
        # Always include crop-agnostic chunks
        if any(chunk_id.startswith(p) for p in _CROP_AGNOSTIC_PREFIXES):
            filtered.append(chunk)
            continue
        # Include chunks that match this crop's prefixes (if any defined)
        if crop_prefixes and any(chunk_id.startswith(p) for p in crop_prefixes):
            filtered.append(chunk)

    logger.debug(
        "Crop filter '%s' (prefixes=%s): %d/%d chunks retained",
        crop, crop_prefixes, len(filtered), len(KNOWLEDGE_CHUNKS),
    )
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(
    query:  str,
    top_k:  int | None = None,
    intent: str = "general",
    crop:   str | None = None,
) -> list[dict]:
    """
    Retrieve the top-K most relevant knowledge chunks for *query*.

    Parameters
    ----------
    query   : English query text.
    top_k   : Number of chunks to return (default: settings.top_k_chunks).
    intent  : Detected farming intent — controls category boosting.
              One of: weather / disease / spraying / fertilizer / irrigation /
                      market / yield / soil / seed / scheme / general
    crop    : Detected crop name (e.g. "paddy", "cotton") — controls
              pre-filtering so only crop-relevant chunks enter scoring.
              Pass None to score all chunks (multi-crop or general queries).

    Returns
    -------
    List of chunk dicts with an added 'score' key, sorted by score desc.

    Examples
    --------
    "paddy price today"         intent=market  crop=paddy  → rice_+market_ chunks
    "yield estimation per acre" intent=yield   crop=paddy  → rice_+agnostic only
    "yellow leaves on rice"     intent=disease crop=paddy  → rice_+disease_ chunks
    "how much urea for cotton"  intent=fert    crop=cotton → cotton_+agnostic chunks
    "groundnut tikka disease"   intent=disease crop=gnut   → gnut_+disease_ chunks
    """
    from chat.config import settings
    k = top_k or settings.top_k_chunks

    if not query.strip():
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    query_counter = Counter(query_tokens)

    # ── ✅ FIX 5: Crop-aware pre-filter ──────────────────────────────────────
    # Filter the candidate pool BEFORE TF-IDF scoring.
    # This is the critical step that prevents cross-crop contamination.
    candidate_chunks = _apply_crop_filter(crop)

    scored = []
    for chunk in candidate_chunks:
        score = _score_chunk(chunk, query_tokens, query_counter, intent)
        if score > 0:
            result          = dict(chunk)
            result["score"] = round(score, 4)
            scored.append(result)

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:k]

    logger.debug(
        "RAG retrieved %d/%d chunks | query='%s...' | intent=%s | crop=%s | "
        "top agent=%s score=%.4f",
        len(top),
        len(candidate_chunks),
        query[:50],
        intent,
        crop or "none",
        top[0].get("agent", "?") if top else "none",
        top[0].get("score", 0)   if top else 0,
    )
    return top


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a prompt context block."""
    if not chunks:
        return "No specific knowledge base context found. Use your agricultural expertise."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Source {i}: {chunk['source']}]\n{chunk['content']}")
    return "\n\n".join(parts)


def get_agent_from_chunks(chunks: list[dict]) -> str:
    """Infer agent type from the highest-scoring retrieved chunk."""
    if not chunks:
        return "general"
    return chunks[0].get("agent", "general")


# ── Backward compat: build_index() is now a no-op ─────────────────────────────
def build_index() -> None:
    """No-op: kept for backward compatibility with app.py startup calls."""
    logger.info(
        "RAG pipeline: keyword scoring (no FAISS). %d chunks loaded.",
        len(KNOWLEDGE_CHUNKS),
    )