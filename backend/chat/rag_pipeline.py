"""
rag_pipeline.py
───────────────
Lightweight keyword-based retrieval for static KNOWLEDGE_CHUNKS.

WHY NOT FAISS?
  The knowledge base is a small static Python list (~30 chunks).
  SentenceTransformer + FAISS uses ~250 MB RAM — crashes Render free tier (512 MB).
  Keyword TF-IDF scoring is equally effective for a small fixed corpus and uses < 5 MB.

Flow:
  1. At query time: score each chunk against the query using keyword overlap + TF weighting
  2. Boost chunks whose "agent" type matches detected intent
  3. Return top-K chunks to farming_agent for Gemini prompt construction
"""

from __future__ import annotations

import re
import math
import logging
from collections import Counter

from chat.knowledge_base import KNOWLEDGE_CHUNKS

logger = logging.getLogger(__name__)

# ── Pre-compute TF-IDF style token frequencies at import time (fast, < 1ms) ──
_STOPWORDS = {
    "the", "a", "an", "is", "in", "of", "to", "and", "or", "for",
    "on", "at", "by", "from", "are", "was", "with", "that", "this",
    "it", "as", "be", "can", "will", "per", "use", "used", "also",
    "have", "has", "not", "no", "if", "its", "than", "each", "all",
}

def _tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split into tokens, remove stopwords."""
    tokens = re.findall(r'\b[a-z]{2,}\b', text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _build_idf() -> dict[str, float]:
    """Compute inverse document frequency for all terms in the corpus."""
    n = len(KNOWLEDGE_CHUNKS)
    df: dict[str, int] = {}
    for chunk in KNOWLEDGE_CHUNKS:
        terms = set(_tokenize(chunk["content"] + " " + chunk.get("topic", "")))
        for term in terms:
            df[term] = df.get(term, 0) + 1
    return {term: math.log(n / count + 1) for term, count in df.items()}


# Pre-compute once at module import (< 1ms, no ML model needed)
_IDF = _build_idf()


def _score_chunk(chunk: dict, query_tokens: list[str], query_counter: Counter) -> float:
    """Score a single chunk against the query using TF-IDF weighted overlap."""
    chunk_text = chunk["content"] + " " + chunk.get("topic", "") + " " + chunk.get("id", "")
    chunk_tokens = _tokenize(chunk_text)
    chunk_counter = Counter(chunk_tokens)
    chunk_len = max(len(chunk_tokens), 1)

    score = 0.0
    for term in query_tokens:
        if term in chunk_counter:
            tf = chunk_counter[term] / chunk_len
            idf = _IDF.get(term, 1.0)
            query_weight = query_counter[term]
            score += tf * idf * query_weight

    return score


def _detect_intent(query_tokens: list[str]) -> str:
    """
    Detect the likely agent type from the query to boost relevant chunks.
    Returns: 'disease' | 'market' | 'general'
    """
    disease_terms = {
        "disease", "pest", "insect", "fungal", "virus", "blight", "blast",
        "rot", "mold", "mould", "rust", "wilt", "spot", "spots", "lesion",
        "yellowing", "browning", "holes", "larvae", "larva", "caterpillar",
        "aphid", "thrip", "whitefly", "hopper", "bollworm", "symptom",
        "spray", "fungicide", "pesticide", "insecticide", "treatment",
        "infected", "infection", "attack", "damage"
    }
    market_terms = {
        "price", "prices", "cost", "msp", "market", "mandi", "rate", "rates",
        "sell", "selling", "buy", "buying", "quintal", "rupee", "rs", "₹",
        "scheme", "subsidy", "loan", "kcc", "kisan", "pm", "pmkisan",
        "income", "profit", "earn", "trade", "export", "enam", "markfed"
    }

    token_set = set(query_tokens)
    disease_hits = len(token_set & disease_terms)
    market_hits = len(token_set & market_terms)

    if disease_hits > market_hits and disease_hits > 0:
        return "disease"
    if market_hits > disease_hits and market_hits > 0:
        return "market"
    return "general"


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """
    Retrieve the top-K most relevant knowledge chunks for *query* (English).

    Uses lightweight keyword TF-IDF scoring — no ML model, no FAISS.
    Returns a list of chunk dicts with an added 'score' key.
    """
    from chat.config import settings
    k = top_k or settings.top_k_chunks

    if not query.strip():
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    query_counter = Counter(query_tokens)
    intent = _detect_intent(query_tokens)

    scored = []
    for chunk in KNOWLEDGE_CHUNKS:
        score = _score_chunk(chunk, query_tokens, query_counter)

        # Boost chunks matching detected intent (disease/market/general)
        chunk_agent = chunk.get("agent", "general")
        if chunk_agent == intent:
            score *= 1.5
        elif intent == "disease" and chunk_agent == "disease":
            score *= 2.0
        elif intent == "market" and chunk_agent == "market":
            score *= 2.0

        if score > 0:
            result = dict(chunk)
            result["score"] = round(score, 4)
            scored.append(result)

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[:k]
    logger.debug(
        "Keyword RAG retrieved %d chunks for query '%s...' (intent: %s)",
        len(top), query[:60], intent
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
    """
    No-op: kept for backward compatibility with app.py startup calls.
    Keyword retrieval needs no pre-built index.
    """
    logger.info(
        "RAG pipeline: using lightweight keyword scoring (no FAISS/sentence-transformers). "
        "%d knowledge chunks loaded.", len(KNOWLEDGE_CHUNKS)
    )