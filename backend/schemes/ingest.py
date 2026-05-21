# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/ingest.py
#
# Builds FAISS + ChromaDB indexes from:
#   1. PDFs in data/scheme_pdfs/  (if available)
#   2. Static knowledge base in static_kb.py (always — works without PDFs)
#
# Usage:
#   cd backend
#   python -m schemes.ingest
# =============================================================================

from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain_core.documents import Document

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent
PDF_DIR       = BASE_DIR / "data" / "scheme_pdfs"
FAISS_DIR     = BASE_DIR / "data" / "scheme_faiss"
CHROMA_DIR    = BASE_DIR / "data" / "scheme_chroma"

# ── LangChain config ──────────────────────────────────────────────────────────
EMBED_MODEL   = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 600
CHUNK_OVERLAP = 120


def _build_from_static_kb() -> list[Document]:
    """
    Convert the static_kb.py knowledge base into LangChain Documents.
    This works immediately without any PDFs.
    """
    from schemes.static_kb import SCHEMES_KB
    docs = []
    for entry in SCHEMES_KB:
        # Create one Document per language variant so the retriever can match any
        for lang_key, lang_label in [
            ("content_en", "English"),
            ("content_hi", "Hindi"),
            ("content_te", "Telugu"),
        ]:
            text = entry.get(lang_key, entry.get("content_en", ""))
            if not text.strip():
                continue
            docs.append(Document(
                page_content=text.strip(),
                metadata={
                    "source": entry.get("source", "static_kb"),
                    "scheme_name": entry.get("name", ""),
                    "scheme_type": entry.get("type", ""),
                    "state": entry.get("state", "all"),
                    "language": lang_label,
                    "page": 0,
                },
            ))
    return docs


def _build_from_pdfs() -> list[Document]:
    """Load and split PDFs from data/scheme_pdfs/ (optional)."""
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        return []

    from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    print(f"[Schemes Ingest] Found {len(pdf_files)} PDF(s):")
    for p in pdf_files:
        print(f"  • {p.name}")

    print("\n[Schemes Ingest] Loading PDFs via LangChain...")
    loader = DirectoryLoader(
        str(PDF_DIR),
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
    )
    raw_docs = loader.load()
    print(f"[Schemes Ingest] Loaded {len(raw_docs)} raw pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "।", ".", " ", ""],
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"[Schemes Ingest] Total PDF chunks: {len(chunks)}")
    return chunks


def build_index():
    print("\n[Schemes Ingest] Starting index build...")

    # ── 1. Collect documents ──────────────────────────────────────────────────
    # Always include static KB docs
    print("[Schemes Ingest] Building documents from static knowledge base...")
    static_docs = _build_from_static_kb()
    print(f"[Schemes Ingest] Static KB: {len(static_docs)} documents")

    # Optionally add PDFs
    pdf_docs = _build_from_pdfs()

    all_docs = static_docs + pdf_docs
    if not all_docs:
        print("[Schemes Ingest] [ERROR] No documents to index!")
        return

    print(f"[Schemes Ingest] Total documents to embed: {len(all_docs)}")

    # ── 2. Embeddings ─────────────────────────────────────────────────────────
    print(f"[Schemes Ingest] Loading embedder: {EMBED_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    print("[Schemes Ingest] Embeddings ready.")

    # ── 3. Save to FAISS (primary) ────────────────────────────────────────────
    print("[Schemes Ingest] Building FAISS index...")
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    faiss_store = FAISS.from_documents(all_docs, embeddings)
    faiss_store.save_local(str(FAISS_DIR))
    print(f"[Schemes Ingest] OK: FAISS saved -> {FAISS_DIR}")

    # ── 4. Save to ChromaDB (fallback) ────────────────────────────────────────
    print("[Schemes Ingest] Building ChromaDB index...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # Delete existing ChromaDB to avoid conflicts on re-run
    import shutil
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    chroma_store = Chroma.from_documents(
        all_docs,
        embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="scheme_docs",
    )
    # Note: newer chromadb versions auto-persist; call persist() for compatibility
    try:
        chroma_store.persist()
    except Exception:
        pass  # Auto-persisted in newer chromadb versions

    print(f"[Schemes Ingest] OK: ChromaDB saved -> {CHROMA_DIR}")
    print(f"\n[Schemes Ingest] Done! {len(all_docs)} documents indexed in FAISS + ChromaDB.\n")


if __name__ == "__main__":
    build_index()
