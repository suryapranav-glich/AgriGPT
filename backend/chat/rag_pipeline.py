"""
rag_pipeline.py
───────────────
FAISS-based Retrieval-Augmented Generation pipeline.

Flow:
  1. At startup: embed all knowledge chunks with sentence-transformers
  2. At query time: embed the user's (English-translated) query
  3. FAISS cosine search → top-K chunks
  4. Return chunks to farming_agent for Gemini prompt construction
"""

from __future__ import annotations

import logging
import numpy as np

from chat.config import settings
from chat.knowledge_base import KNOWLEDGE_CHUNKS

logger = logging.getLogger(__name__)

# ── Module-level singletons (loaded once at startup) ─────────────────────────
_model = None          # SentenceTransformer
_index = None          # faiss.Index
_metadata: list[dict] = []


def _cosine_normalise(vectors: np.ndarray) -> np.ndarray:
    """L2-normalise so inner product == cosine similarity."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vectors / norms


def build_index() -> None:
    """
    Load embedding model and build FAISS index from KNOWLEDGE_CHUNKS.
    Called once at FastAPI startup.
    """
    global _model, _index, _metadata
    import faiss
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", settings.embedding_model)
    _model = SentenceTransformer(settings.embedding_model)

    texts = [chunk["content"] for chunk in KNOWLEDGE_CHUNKS]
    logger.info("Embedding %d knowledge chunks…", len(texts))

    embeddings = _model.encode(texts, batch_size=16, show_progress_bar=False)
    embeddings = _cosine_normalise(embeddings.astype("float32"))

    dim = embeddings.shape[1]
    _index = faiss.IndexFlatIP(dim)   # Inner Product on normalised vecs = cosine
    _index.add(embeddings)

    _metadata = KNOWLEDGE_CHUNKS
    logger.info("FAISS index built with %d chunks (dim=%d)", _index.ntotal, dim)


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """
    Retrieve the top-K most relevant knowledge chunks for *query* (English).

    Returns a list of chunk dicts with an added 'score' key.
    """
    if _index is None or _model is None:
        logger.warning("RAG index not built — returning empty context.")
        return []

    k = top_k or settings.top_k_chunks

    q_emb = _model.encode([query], show_progress_bar=False)
    q_emb = _cosine_normalise(q_emb.astype("float32"))

    scores, indices = _index.search(q_emb, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = dict(_metadata[idx])
        chunk["score"] = float(score)
        results.append(chunk)

    logger.debug("RAG retrieved %d chunks for query: %s…", len(results), query[:60])
    return results


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a prompt context block."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}: {chunk['source']}]\n{chunk['content']}"
        )
    return "\n\n".join(parts)


def get_agent_from_chunks(chunks: list[dict]) -> str:
    """Infer agent type from the highest-scoring retrieved chunk."""
    if not chunks:
        return "general"
    return chunks[0].get("agent", "general")
