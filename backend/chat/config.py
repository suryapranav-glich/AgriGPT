import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── API Keys ──────────────────────────────────────────────────────────────
    gemini_api_key: str = ""        # Used for IMAGE understanding only
    groq_api_key: str = ""          # Used for TEXT chat, Q&A, recommendations
    google_translate_api_key: str = ""
    
    # ── App config ────────────────────────────────────────────────────────────
    frontend_origin: str = "https://agrigpt-xi.vercel.app"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    use_indic_trans2: bool = False
    top_k_chunks: int = 6
    max_response_tokens: int = 2048

    # ── Model names ───────────────────────────────────────────────────────────
    groq_model: str = "llama-3.1-8b-instant"          # Fast, 14400 req/day free
    gemini_model: str = "gemini-2.0-flash"             # For image/multimodal

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "extra": "ignore"
    }

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

UNICODE_SCRIPT_MAP: list[tuple[range, str]] = [
    (range(0x0C00, 0x0C80), "te"),
    (range(0x0900, 0x0980), "hi"),
    (range(0x0B80, 0x0C00), "ta"),
    (range(0x0C80, 0x0D00), "kn"),
    (range(0x0D00, 0x0D80), "ml"),
    (range(0x0980, 0x0A00), "bn"),
    (range(0x0A80, 0x0B00), "gu"),
    (range(0x0A00, 0x0A80), "pa"),
    (range(0x0B00, 0x0B80), "or"),
    (range(0x0600, 0x0700), "ur"),
]

PHASE1_LANGUAGES = {"en", "hi", "te"}