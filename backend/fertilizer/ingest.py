# =============================================================================
# AgriGPT — Feature 3: Fertilizer Recommendation Engine
# fertilizer/ingest.py
#
# Run ONCE to ingest ICAR PDF files into a FAISS vector index.
# After adding new PDFs, re-run this script to rebuild the index.
#
# Usage:
#   cd backend
#   python -m fertilizer.ingest
# =============================================================================

import os
import re
import json
import numpy as np
from pathlib import Path

import faiss
import pypdf
from sentence_transformers import SentenceTransformer

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent   # backend/
PDF_DIR    = BASE_DIR / "data" / "icar_pdfs"
INDEX_DIR  = BASE_DIR / "data" / "faiss_index"

# ── Chunking config ───────────────────────────────────────────────────────────
CHUNK_SIZE   = 600    # characters per chunk
OVERLAP      = 120    # overlap between consecutive chunks
MIN_CHUNK    = 80     # discard chunks shorter than this

EMBED_MODEL  = "all-MiniLM-L6-v2"   # fast, good retrieval quality


# =============================================================================
# 1. PDF TEXT EXTRACTION
# =============================================================================
def extract_text(pdf_path: Path) -> str:
    """Extract all text from a PDF, page by page."""
    reader = pypdf.PdfReader(str(pdf_path))
    pages  = []
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        # Clean up hyphenated line-breaks and excessive whitespace
        txt = re.sub(r"-\n", "", txt)
        txt = re.sub(r"\n+", " ", txt)
        txt = re.sub(r" {2,}", " ", txt)
        pages.append(txt.strip())
    return " ".join(pages)


# =============================================================================
# 2. CHUNKING  (sliding window with overlap)
# =============================================================================
def chunk_text(text: str, source: str) -> list[dict]:
    """
    Split text into overlapping windows.
    Each chunk carries its source PDF filename as metadata.
    """
    chunks = []
    start  = 0
    while start < len(text):
        end   = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK:
            chunks.append({"text": chunk, "source": source})
        start += CHUNK_SIZE - OVERLAP
    return chunks


# =============================================================================
# 3. BUILD & SAVE FAISS INDEX
# =============================================================================
def build_index():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(
            f"\n[Ingest] ⚠  No PDFs found in  {PDF_DIR}\n"
            "  → Download ICAR nutrient management PDFs and place them there,\n"
            "    then re-run:  python -m fertilizer.ingest\n"
            "  → The API will use the static knowledge base until an index exists.\n"
        )
        return

    # ── Extract & chunk ──────────────────────────────────────────────────────
    all_chunks: list[dict] = []
    for pdf_path in pdf_files:
        print(f"[Ingest] Reading  {pdf_path.name} …")
        text   = extract_text(pdf_path)
        chunks = chunk_text(text, source=pdf_path.name)
        all_chunks.extend(chunks)
        print(f"  → {len(chunks)} chunks extracted")

    print(f"\n[Ingest] Total chunks : {len(all_chunks)}")

    # ── Embed ────────────────────────────────────────────────────────────────
    print(f"[Ingest] Embedding with {EMBED_MODEL} …")
    embedder   = SentenceTransformer(EMBED_MODEL)
    texts      = [c["text"] for c in all_chunks]
    embeddings = embedder.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,   # cosine similarity via dot product
    ).astype(np.float32)

    # ── FAISS index (Inner Product = cosine on normalised vectors) ────────────
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"[Ingest] FAISS index: {index.ntotal} vectors (dim={dim})")

    # ── Save ─────────────────────────────────────────────────────────────────
    faiss.write_index(index, str(INDEX_DIR / "icar.index"))
    with open(INDEX_DIR / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"[Ingest] ✅ Saved  →  {INDEX_DIR}/icar.index  +  chunks.json\n")


# =============================================================================
# 4. ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    build_index()
