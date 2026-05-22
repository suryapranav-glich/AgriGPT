import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = ""
    google_translate_api_key: str = ""
    frontend_origin: str = "http://localhost:5173"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    use_indic_trans2: bool = False
    top_k_chunks: int = 6          # RAG: how many chunks to retrieve
    max_response_tokens: int = 2048

    model_config = {"env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), "extra": "ignore"}

settings = Settings()

# ── Indian language code → display name (all 22 scheduled languages) ──────────
LANGUAGE_MAP: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "ur": "Urdu",
    "sa": "Sanskrit",
    "ks": "Kashmiri",
    "sd": "Sindhi",
    "kok": "Konkani",
    "mni": "Manipuri",
    "brx": "Bodo",
    "sat": "Santali",
    "mai": "Maithili",
    "doi": "Dogri",
    "ne": "Nepali",
}

# Unicode block → (lang_code) — most reliable detection for Indic scripts
UNICODE_SCRIPT_MAP: list[tuple[range, str]] = [
    (range(0x0C00, 0x0C80), "te"),   # Telugu
    (range(0x0900, 0x0980), "hi"),   # Devanagari (Hindi/Marathi/Sanskrit)
    (range(0x0B80, 0x0C00), "ta"),   # Tamil
    (range(0x0C80, 0x0D00), "kn"),   # Kannada
    (range(0x0D00, 0x0D80), "ml"),   # Malayalam
    (range(0x0980, 0x0A00), "bn"),   # Bengali
    (range(0x0A80, 0x0B00), "gu"),   # Gujarati
    (range(0x0A00, 0x0A80), "pa"),   # Gurmukhi (Punjabi)
    (range(0x0B00, 0x0B80), "or"),   # Odia
    (range(0x0600, 0x0700), "ur"),   # Arabic script (Urdu/Kashmiri)
]

# Phase-1 languages with full RAG + Gemini support
PHASE1_LANGUAGES = {"en", "hi", "te"}
