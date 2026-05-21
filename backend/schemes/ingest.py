# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/ingest.py
#
# LangChain-based PDF ingestion:
#   1. Loads PDFs via LangChain DirectoryLoader + PyPDFLoader
#   2. Splits with RecursiveCharacterTextSplitter
#   3. Embeds with HuggingFaceEmbeddings (all-MiniLM-L6-v2)
#   4. Saves to FAISS (primary) + ChromaDB (fallback)
#
# Usage:
#   cd backend
#   python -m schemes.ingest
# =============================================================================

from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS, Chroma

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent
PDF_DIR       = BASE_DIR / "data" / "scheme_pdfs"
FAISS_DIR     = BASE_DIR / "data" / "scheme_faiss"
CHROMA_DIR    = BASE_DIR / "data" / "scheme_chroma"

# ── LangChain config ──────────────────────────────────────────────────────────
EMBED_MODEL   = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 600
CHUNK_OVERLAP = 120

# Recommended PDFs to place in data/scheme_pdfs/:
# • PM-KISAN operational guidelines PDF
# • PMFBY guidelines PDF
# • Rythu Bandhu scheme document (Telangana)
# • YSR Rythu Bharosa guidelines (AP)
# • PMKSY operational guidelines
# • State agriculture budget documents


def build_index():
    # ── Check PDFs ────────────────────────────────────────────────────────────
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(
            f"\n[Schemes Ingest] [WARNING] No PDFs found in: {PDF_DIR}\n"
            "  Place government scheme PDFs there, then re-run:\n"
            "      python -m schemes.ingest\n"
            "  Static knowledge base will be used until then.\n"
        )
        return

    print(f"[Schemes Ingest] Found {len(pdf_files)} PDF(s):")
    for p in pdf_files:
        print(f"  • {p.name}")

    # ── Load via LangChain DirectoryLoader + PyPDFLoader ─────────────────────
    print("\n[Schemes Ingest] Loading PDFs via LangChain...")
    loader = DirectoryLoader(
        str(PDF_DIR),
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
    )
    raw_docs = loader.load()
    print(f"[Schemes Ingest] Loaded {len(raw_docs)} raw pages")

    # ── Split with RecursiveCharacterTextSplitter ─────────────────────────────
    print("[Schemes Ingest] Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators    = ["\n\n", "\n", "।", ".", " ", ""],  # includes Hindi separator
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"[Schemes Ingest] Total chunks: {len(chunks)}")

    # ── Embed with HuggingFaceEmbeddings ─────────────────────────────────────
    print(f"[Schemes Ingest] Loading embedder: {EMBED_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name      = EMBED_MODEL,
        model_kwargs    = {"device": "cpu"},
        encode_kwargs   = {"normalize_embeddings": True},
    )

    # ── Save to FAISS (primary) ───────────────────────────────────────────────
    print("[Schemes Ingest] Building FAISS index...")
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    faiss_store = FAISS.from_documents(chunks, embeddings)
    faiss_store.save_local(str(FAISS_DIR))
    print(f"[Schemes Ingest] OK: FAISS saved -> {FAISS_DIR}")

    # ── Save to ChromaDB (fallback) ───────────────────────────────────────────
    print("[Schemes Ingest] Building ChromaDB index...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma_store = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory = str(CHROMA_DIR),
        collection_name   = "scheme_docs",
    )
    chroma_store.persist()
    print(f"[Schemes Ingest] OK: ChromaDB saved -> {CHROMA_DIR}")

    print(f"\n[Schemes Ingest] Done. {len(chunks)} chunks indexed in both FAISS and ChromaDB.\n")


if __name__ == "__main__":
    build_index()
