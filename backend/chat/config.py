"""config.py
─────────────────────────────────────────────────────────────────────────────
All configurable values live here — nothing hardcoded in farming_agent.py.
Set values via environment variables or a .env file.

Supported languages: English (en) | Hindi (hi) | Telugu (te)

Free API key for live mandi prices:  https://data.gov.in/user/register

Improvements in this version
  ✅  top_k_chunks reduced to 4 (less noise, better precision)
  ✅  Chunk metadata schema defined (crop / category / language / season)
  ✅  BASE_SYSTEM_PROMPT + thin language wrappers (single source of truth)
  ✅  Conversation memory dataclass + helpers
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_MAP: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "bn": "Bengali",
    "ml": "Malayalam",
    "or": "Odia",
    "ur": "Urdu",
}

# Languages with full system prompt + UI string support
SUPPORTED_LANGUAGES: list[str] = ["en", "hi", "te"]

LangCode = Literal["en", "hi", "te"]


# ─────────────────────────────────────────────────────────────────────────────
# MSP 2024-25 RATES  (CACP official)
# Key   = lowercase crop name used internally
# Value = {grade_label: price_per_quintal}  ("" = single-grade crop)
# ─────────────────────────────────────────────────────────────────────────────

_MSP_RATES: dict[str, dict[str, int]] = {
    "paddy":     {"Common": 2300, "Grade A": 2320},
    "rice":      {"Common": 2300, "Grade A": 2320},
    "wheat":     {"": 2275},
    "cotton":    {"Medium Staple": 7121, "Long Staple": 7521},
    "maize":     {"": 2225},
    "soybean":   {"Yellow": 4892},
    "groundnut": {"": 6783},
    "jowar":     {"Hybrid": 3371, "Maldandi": 3421},
    "bajra":     {"": 2625},
    "ragi":      {"": 4290},
    "tur":       {"": 7550},
    "arhar":     {"": 7550},
    "moong":     {"": 8682},
    "urad":      {"": 7400},
    "mustard":   {"": 5950},
    "sunflower": {"": 7280},
    "sesame":    {"": 9267},
    "gram":      {"": 5440},
    "masur":     {"": 6425},
    "barley":    {"": 1735},
}


# ─────────────────────────────────────────────────────────────────────────────
# AGMARKNET COMMODITY MAP
# Key = internal crop key  →  Value = exact commodity string in AgMarkNet API
# ─────────────────────────────────────────────────────────────────────────────

_AGMARKNET_CROP_MAP: dict[str, str] = {
    "paddy":       "Paddy(Dhan)(Common)",
    "rice":        "Paddy(Dhan)(Common)",
    "wheat":       "Wheat",
    "cotton":      "Cotton",
    "maize":       "Maize",
    "corn":        "Maize",
    "soybean":     "Soybean",
    "groundnut":   "Groundnut",
    "onion":       "Onion",
    "tomato":      "Tomato",
    "potato":      "Potato",
    "chilli":      "Dry Chillies",
    "jowar":       "Jowar(Sorghum)",
    "bajra":       "Bajra(Pearl Millet/Cumbu)",
    "ragi":        "Ragi (Finger Millet)",
    "tur":         "Tur Dal(Arhar Dal)",
    "arhar":       "Tur Dal(Arhar Dal)",
    "moong":       "Moong Dal",
    "urad":        "Urad Dal",
    "mustard":     "Rapeseed & Mustard",
    "sunflower":   "Sunflower Seed",
    "sugarcane":   "Sugarcane",
    "banana":      "Banana",
    "mango":       "Mango",
    "brinjal":     "Brinjal",
    "cabbage":     "Cabbage",
    "cauliflower": "Cauliflower",
}


# ─────────────────────────────────────────────────────────────────────────────
# ✅ FIX 2 — CHUNK METADATA SCHEMA
#
# Every document chunk stored in the vector DB must carry this metadata.
# Use it in your retriever to filter BEFORE semantic search, e.g.:
#
#   results = vectordb.query(
#       query_embeddings=[query_vec],
#       n_results=settings.top_k_chunks,           # now 4
#       where={                                     # metadata pre-filter
#           "crop":     detected_crop,              # "paddy"
#           "language": user_lang,                  # "te"
#           "season":   current_season(),           # "kharif"
#       },
#   )
#
# This replaces brute-force top-k with precision retrieval.
# ─────────────────────────────────────────────────────────────────────────────

# Allowed values for each metadata field  (use these as enums in your ingestion
# pipeline so you never store a typo that silently breaks filtering)

CHUNK_CATEGORIES = Literal[
    "disease",       # pest / pathogen identification & treatment
    "fertilizer",    # nutrient management, doses, schedules
    "irrigation",    # water management, scheduling
    "market",        # mandi prices, MSP, selling advice
    "weather",       # climate advisory, spray windows
    "soil",          # soil health, testing, amendments
    "seed",          # variety selection, sowing
    "scheme",        # govt schemes, subsidies, insurance
    "general",       # catch-all
]

CHUNK_SEASONS = Literal["kharif", "rabi", "zaid", "perennial", "all"]

@dataclass
class ChunkMetadata:
    """
    Attach one of these to every chunk at ingestion time.

    Example
    -------
    meta = ChunkMetadata(
        crop="paddy",
        category="disease",
        language="te",
        season="kharif",
        source="icar_paddy_2024.pdf",
        page=12,
    )
    vectordb.add(documents=[chunk_text], metadatas=[meta.to_dict()], ids=[chunk_id])
    """
    crop:     str   = "all"        # lowercase internal key, e.g. "paddy"
    category: str   = "general"    # one of CHUNK_CATEGORIES
    language: str   = "en"         # "en" | "hi" | "te" | "all"
    season:   str   = "all"        # one of CHUNK_SEASONS
    source:   str   = ""           # file name or URL
    page:     int   = 0            # page number (0 = unknown)

    def to_dict(self) -> dict[str, str | int]:
        return {
            "crop":     self.crop,
            "category": self.category,
            "language": self.language,
            "season":   self.season,
            "source":   self.source,
            "page":     self.page,
        }

    @staticmethod
    def build_filter(
        crop: str | None     = None,
        category: str | None = None,
        language: str | None = None,
        season: str | None   = None,
    ) -> dict:
        """
        Build a ChromaDB-compatible `where` filter dict.
        Only adds keys that are explicitly provided.

        Usage in retriever
        ------------------
        where = ChunkMetadata.build_filter(crop="paddy", language="te")
        results = collection.query(query_embeddings=[q], n_results=4, where=where)
        """
        f: dict = {}
        if crop:     f["crop"]     = crop
        if category: f["category"] = category
        if language and language != "en":   # en chunks used as fallback always
            f["language"] = {"$in": [language, "all"]}
        if season and season != "all":
            f["season"] = {"$in": [season, "all"]}
        return f


# ─────────────────────────────────────────────────────────────────────────────
# ✅ FIX 3 — BASE SYSTEM PROMPT + THIN LANGUAGE WRAPPERS
#
# One source of truth. Rules change in ONE place only.
# Language wrappers add only:  identity name + response-language instruction.
# ─────────────────────────────────────────────────────────────────────────────

_BASE_RULES: str = """\
YOUR JOB:
Use the REAL-TIME DATA (live mandi prices, live weather) and REFERENCE KNOWLEDGE \
provided to answer the farmer's question with exact numbers.

PRICES:
- Use ONLY the live mandi figures given. Never guess or substitute.
- State market name, state, and date with every price.
- Show price range when multiple markets are listed; highlight the nearest.
- Always compare today's mandi rate to the Govt MSP.
- Never give vague ranges — use exact ₹ figures.

WEATHER:
- Rain ≥ 60 %: advise against spraying today.
- Wind ≥ 25 km/h: warn against foliar sprays.
- UV ≥ 8 or temp ≥ 40 °C: recommend early-morning or evening operations.

GENERAL:
- Address the farmer directly as "you / your crop / your field".
- Lead with the most important advice.
- Use exact quantities, product names, doses, and ₹ figures.
- Bold (**…**) critical numbers, product names, and actions.
- Never recommend banned pesticides: Monocrotophos, Endosulfan.
- Decline non-agriculture questions politely.
- Synthesise — do NOT copy-paste reference text verbatim.\
"""

# Language wrappers — identity + response-language instruction only
_LANG_WRAPPERS: dict[str, str] = {
    "en": (
        "You are KrishiMitra, a knowledgeable and friendly AI agricultural advisor "
        "for Indian farmers.\n\n"
        "{rules}\n\n"
        "RESPOND IN ENGLISH ONLY."
    ),
    "hi": (
        "आप KrishiMitra हैं — भारतीय किसानों के लिए AI कृषि सलाहकार।\n\n"
        "{rules}\n\n"
        "केवल हिंदी में उत्तर दें।"
    ),
    "te": (
        "మీరు KrishiMitra — భారతీయ రైతులకు AI వ్యవసాయ సలహాదారు.\n\n"
        "{rules}\n\n"
        "తెలుగులో మాత్రమే సమాధానం ఇవ్వండి."
    ),
}

def get_system_prompt(lang: str) -> str:
    """
    Compose the system prompt for *lang* by injecting _BASE_RULES
    into the thin language wrapper.  Falls back to English.

    >>> get_system_prompt("te")          # Telugu prompt, ~30 lines
    >>> get_system_prompt("xx")          # falls back to English
    """
    wrapper = _LANG_WRAPPERS.get(lang, _LANG_WRAPPERS["en"])
    return wrapper.format(rules=_BASE_RULES)


# ─────────────────────────────────────────────────────────────────────────────
# TRILINGUAL USER-FACING STATIC MESSAGES
# ─────────────────────────────────────────────────────────────────────────────

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "non_agri_reject":    (
            "I am KrishiMitra, your AI agricultural advisor. I can only help with "
            "farming, crops, soil, weather, and market queries. "
            "Please ask me anything related to agriculture."
        ),
        "llm_unavailable":    (
            "The advisory service is currently unavailable. "
            "Please try again shortly or contact your local Krishi Vigyan Kendra."
        ),
        "llm_error":          (
            "I ran into a technical issue generating your answer. "
            "Please try again or reach out to your local KVK for immediate help."
        ),
        "msp_below":          (
            "⚠ If any mandi bids BELOW the MSP, sell through RBK / FCI — "
            "the government guarantees the MSP price by law."
        ),
        "mandi_unavailable":  (
            "⚠ Live mandi data is temporarily unavailable. "
            "Showing Govt MSP as reference."
        ),
        "mandi_check":        "For today's live rates: agmarknet.gov.in → Commodity Prices",
        "greeting":           (
            "Namaste! I am KrishiMitra, your AI farming advisor. "
            "Ask me about crop prices, weather, disease, or farming advice."
        ),
        "language_prompt":    (
            "Please choose your preferred language:\n"
            "1. English\n2. हिंदी (Hindi)\n3. తెలుగు (Telugu)"
        ),
        "memory_context_header": "CONVERSATION SO FAR:\n",
        "memory_summary_prompt": (
            "Summarise the key farming facts established in this conversation "
            "(crop, location, problem, decisions made). Be concise — 3-5 bullet points."
        ),
    },
    "hi": {
        "non_agri_reject":    (
            "मैं KrishiMitra हूं, आपका AI कृषि सलाहकार। मैं केवल खेती, फसल, "
            "मिट्टी, मौसम और बाजार संबंधी प्रश्नों में सहायता कर सकता हूं।"
        ),
        "llm_unavailable":    (
            "सलाह सेवा अभी उपलब्ध नहीं है। कृपया थोड़ी देर बाद पुनः प्रयास करें "
            "या अपने स्थानीय कृषि विज्ञान केंद्र से संपर्क करें।"
        ),
        "llm_error":          (
            "आपका उत्तर तैयार करने में तकनीकी समस्या आई। कृपया पुनः प्रयास करें "
            "या तत्काल सहायता के लिए अपने स्थानीय KVK से संपर्क करें।"
        ),
        "msp_below":          (
            "⚠ यदि कोई मंडी MSP से नीचे भाव दे, तो RBK / FCI के माध्यम से बेचें — "
            "सरकार कानूनी रूप से MSP की गारंटी देती है।"
        ),
        "mandi_unavailable":  (
            "⚠ लाइव मंडी डेटा अभी उपलब्ध नहीं है। सरकारी MSP संदर्भ के रूप में दिखाया जा रहा है।"
        ),
        "mandi_check":        "आज के लाइव भाव: agmarknet.gov.in → Commodity Prices",
        "greeting":           (
            "नमस्ते! मैं KrishiMitra हूं, आपका AI कृषि सलाहकार। "
            "फसल भाव, मौसम, रोग या खेती की सलाह के बारे में पूछें।"
        ),
        "language_prompt":    (
            "कृपया अपनी पसंदीदा भाषा चुनें:\n"
            "1. English\n2. हिंदी (Hindi)\n3. తెలుగు (Telugu)"
        ),
        "memory_context_header": "अब तक की बातचीत:\n",
        "memory_summary_prompt": (
            "इस बातचीत में स्थापित मुख्य कृषि तथ्यों का सारांश दें "
            "(फसल, स्थान, समस्या, लिए गए निर्णय)। संक्षेप में — 3-5 बुलेट पॉइंट।"
        ),
    },
    "te": {
        "non_agri_reject":    (
            "నేను KrishiMitra, మీ AI వ్యవసాయ సలహాదారుడను. నేను వ్యవసాయం, పంటలు, "
            "మట్టి, వాతావరణం మరియు మార్కెట్ సంబంధిత ప్రశ్నలకు మాత్రమే సహాయం చేయగలను."
        ),
        "llm_unavailable":    (
            "సలహా సేవ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కొద్దిసేపు తర్వాత మళ్ళీ "
            "ప్రయత్నించండి లేదా మీ స్థానిక కృషి విజ్ఞాన కేంద్రాన్ని సంప్రదించండి."
        ),
        "llm_error":          (
            "మీ సమాధానం రూపొందించడంలో సాంకేతిక సమస్య వచ్చింది. దయచేసి మళ్ళీ "
            "ప్రయత్నించండి లేదా తక్షణ సహాయం కోసం మీ స్థానిక KVKని సంప్రదించండి."
        ),
        "msp_below":          (
            "⚠ ఏదైనా మండి MSP కంటే తక్కువ ధర ఇస్తే, RBK / FCI ద్వారా అమ్మండి — "
            "ప్రభుత్వం చట్టపరంగా MSP ధరకు హామీ ఇస్తుంది."
        ),
        "mandi_unavailable":  (
            "⚠ లైవ్ మండి డేటా తాత్కాలికంగా అందుబాటులో లేదు. "
            "ప్రభుత్వ MSPని సూచనగా చూపిస్తున్నాం."
        ),
        "mandi_check":        "ఈరోజు లైవ్ ధరల కోసం: agmarknet.gov.in → Commodity Prices",
        "greeting":           (
            "నమస్కారం! నేను KrishiMitra, మీ AI వ్యవసాయ సలహాదారుడను. "
            "పంట ధరలు, వాతావరణం, వ్యాధి లేదా వ్యవసాయ సలహా గురించి అడగండి."
        ),
        "language_prompt":    (
            "దయచేసి మీకు నచ్చిన భాష ఎంచుకోండి:\n"
            "1. English\n2. हिंदी (Hindi)\n3. తెలుగు (Telugu)"
        ),
        "memory_context_header": "ఇప్పటివరకు జరిగిన సంభాషణ:\n",
        "memory_summary_prompt": (
            "ఈ సంభాషణలో స్థాపించిన ముఖ్యమైన వ్యవసాయ విషయాలను సంగ్రహించండి "
            "(పంట, స్థానం, సమస్య, తీసుకున్న నిర్ణయాలు). సంక్షిప్తంగా — 3-5 అంశాలు."
        ),
    },
}


def get_message(lang: str, key: str) -> str:
    """Return a translated user-facing string.  Falls back to English."""
    return _MESSAGES.get(lang, _MESSAGES["en"]).get(
        key, _MESSAGES["en"].get(key, "")
    )


# ─────────────────────────────────────────────────────────────────────────────
# ✅ FIX 4 — CONVERSATION MEMORY
#
# ConversationMemory keeps a sliding window of recent turns + a running
# summary of key farming facts (crop, location, problem, decisions).
#
# Usage in farming_agent.py
# ─────────────────────────────────────────────────────────────────────────────
#
#   memory = ConversationMemory(lang="te")
#
#   # On each user turn:
#   memory.add_turn("user", user_text)
#   context = memory.build_context()         # inject into LLM system prompt
#
#   # On each assistant turn:
#   memory.add_turn("assistant", reply_text)
#
#   # After every N turns, compress:
#   if memory.should_summarise():
#       summary = llm.call(memory.summary_prompt())
#       memory.apply_summary(summary)
#
# ─────────────────────────────────────────────────────────────────────────────

Role = Literal["user", "assistant"]

@dataclass
class Turn:
    role:      Role
    content:   str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_llm_message(self) -> dict[str, str]:
        """Convert to the OpenAI-style message dict expected by the LLM."""
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationMemory:
    """
    Sliding-window conversation memory with periodic summarisation.

    Parameters
    ----------
    lang            Language code — controls header / summary prompt language.
    max_turns       Maximum raw turns to keep before triggering summarisation.
    summarise_every Summarise after this many NEW turns since last summary.
    """
    lang:            str = "en"
    max_turns:       int = 10
    summarise_every: int = 6

    _turns:          list[Turn] = field(default_factory=list, init=False)
    _summary:        str        = field(default="", init=False)
    _turns_since_summary: int   = field(default=0, init=False)

    # ── Detected session context (populated by the agent as it runs) ──────────
    detected_crop:     str | None = field(default=None, init=False)
    detected_location: str | None = field(default=None, init=False)
    detected_season:   str | None = field(default=None, init=False)

    def add_turn(self, role: Role, content: str) -> None:
        """Append a new turn and trim to max_turns."""
        self._turns.append(Turn(role=role, content=content))
        self._turns_since_summary += 1
        # Keep only the most recent max_turns
        if len(self._turns) > self.max_turns:
            self._turns = self._turns[-self.max_turns :]

    def should_summarise(self) -> bool:
        """True when it is time to compress the conversation."""
        return self._turns_since_summary >= self.summarise_every

    def summary_prompt(self) -> str:
        """Return the prompt that asks the LLM to produce a new summary."""
        return get_message(self.lang, "memory_summary_prompt")

    def apply_summary(self, summary_text: str) -> None:
        """Replace the running summary and reset the counter."""
        self._summary = summary_text
        self._turns_since_summary = 0
        # Keep only the last 2 raw turns after summarisation
        self._turns = self._turns[-2:]

    def build_context(self) -> str:
        """
        Produce the memory block to prepend to the system prompt.

        Format injected into every LLM call:

            CONVERSATION SO FAR:
            [Summary if available]

            user: <last message>
            assistant: <last reply>
            ...
        """
        parts: list[str] = []
        header = get_message(self.lang, "memory_context_header")
        parts.append(header)

        if self._summary:
            parts.append(f"Summary: {self._summary}\n")

        for turn in self._turns:
            parts.append(f"{turn.role}: {turn.content}")

        return "\n".join(parts)

    def to_llm_messages(self) -> list[dict[str, str]]:
        """
        Return the conversation as a list of OpenAI-style message dicts.
        Prepend the summary as a system message if one exists.

        Use this when your LLM client accepts a `messages` array directly.
        """
        messages: list[dict[str, str]] = []
        if self._summary:
            messages.append({
                "role":    "system",
                "content": f"Conversation summary: {self._summary}",
            })
        messages.extend(t.to_llm_message() for t in self._turns)
        return messages

    @property
    def last_user_message(self) -> str | None:
        for turn in reversed(self._turns):
            if turn.role == "user":
                return turn.content
        return None

    @property
    def turn_count(self) -> int:
        return len(self._turns)


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS  (Pydantic BaseSettings — all values overridable via .env)
# ─────────────────────────────────────────────────────────────────────────────

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    groq_api_key:    str   = ""
    groq_model:      str   = "llama-3.1-8b-instant"
    gemini_api_key:  str   = ""
    gemini_model:    str   = "gemini-2.0-flash"
    llm_temperature: float = 0.3

    # ── Live data ─────────────────────────────────────────────────────────────
    data_gov_api_key:    str   = ""   # https://data.gov.in/user/register
    agmarknet_base_url:  str   = (
        "https://api.data.gov.in/resource/"
        "9ef84268-d588-465a-a308-a864a43d0070"
    )
    api_timeout_seconds: float = 9.0

    # ── Default location (used when geocoding fails) ───────────────────────────
    default_lat:           float = 17.385
    default_lon:           float = 78.4867
    default_location_name: str   = "Hyderabad, Telangana"

    # ── Default language ───────────────────────────────────────────────────────
    default_language: str = "en"   # "en" | "hi" | "te"

    # ── Weather thresholds for auto-advisories ────────────────────────────────
    rain_spray_block_pct:   float = 60.0
    rain_spray_caution_pct: float = 40.0
    wind_spray_block_kmh:   float = 25.0
    uv_spray_caution:       float = 8.0
    heat_stress_temp_c:     float = 40.0

    # ── RAG / retrieval ───────────────────────────────────────────────────────
    top_k_chunks:        int = 4      # ✅ reduced from 6 → less noise, better precision
    max_response_tokens: int = 1024

    # ── Conversation memory ───────────────────────────────────────────────────
    memory_max_turns:       int = 10  # raw turns kept in sliding window
    memory_summarise_every: int = 6   # compress after N new turns

    # ── MSP data ──────────────────────────────────────────────────────────────
    msp_rates:  dict = _MSP_RATES
    msp_season: str  = "2024-25"

    agmarknet_crop_map: dict = _AGMARKNET_CROP_MAP

    # ── Source labels ─────────────────────────────────────────────────────────
    agmarknet_source_label: str = "AgMarkNet — data.gov.in (Live Prices)"
    openmeteo_source_label: str = "Open-Meteo (Live Weather Forecast)"
    cnn_source_label:       str = "AgriGPT Disease Diagnosis Database 2026"

    # ── Language maps ─────────────────────────────────────────────────────────
    language_map:        dict = LANGUAGE_MAP
    supported_languages: list = SUPPORTED_LANGUAGES

    # ── Convenience methods ───────────────────────────────────────────────────
    def message(self, lang: str, key: str) -> str:
        """settings.message('te', 'greeting')"""
        return get_message(lang, key)

    def system_prompt(self, lang: str) -> str:
        """settings.system_prompt('hi')"""
        return get_system_prompt(lang)

    def new_memory(self, lang: str | None = None) -> ConversationMemory:
        """
        Factory — creates a ConversationMemory wired to Settings values.

        Usage:
            memory = settings.new_memory(lang="te")
        """
        return ConversationMemory(
            lang=lang or self.default_language,
            max_turns=self.memory_max_turns,
            summarise_every=self.memory_summarise_every,
        )


settings = Settings()