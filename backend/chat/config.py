"""config.py
─────────────────────────────────────────────────────────────────────────────
All configurable values live here — nothing hardcoded in farming_agent.py.
Set values via environment variables or a .env file.

Supported languages: English (en) | Hindi (hi) | Telugu (te)

Free API key for live mandi prices:  https://data.gov.in/user/register

Changes in this version
  ✅  groq_model upgraded to llama-3.3-70b-versatile
  ✅  top_k_chunks reduced to 4 (less noise, better precision)
  ✅  Chunk metadata schema defined (crop / category / language / season)
  ✅  BASE_SYSTEM_PROMPT strengthened with CRITICAL LIVE-DATA priority rules
  ✅  INTENT_CATEGORY system added (yield, fertilizer, irrigation, spraying …)
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

SUPPORTED_LANGUAGES: list[str] = ["en", "hi", "te"]

LangCode = Literal["en", "hi", "te"]


# ─────────────────────────────────────────────────────────────────────────────
# INTENT CATEGORIES
#
# Used by detect_intent() in farming_agent.py to:
#   1. Decide which live data feeds to inject (weather only for relevant intents)
#   2. Filter RAG retrieval to matching chunk categories
#   3. Route to the right agent type
#
# INTENT → CHUNK CATEGORIES that should be retrieved
# INTENT → whether live weather should be injected
# ─────────────────────────────────────────────────────────────────────────────

# Intents for which live weather MUST be injected into the prompt
WEATHER_RELEVANT_INTENTS: frozenset[str] = frozenset({
    "weather",
    "disease",
    "spraying",
    "fertilizer",
    "irrigation",
})

# Mapping: intent → list of chunk categories to prioritise in RAG retrieval
INTENT_TO_CHUNK_CATEGORIES: dict[str, list[str]] = {
    "weather":    ["weather", "general"],
    "disease":    ["disease", "general"],
    "spraying":   ["disease", "fertilizer", "weather", "general"],
    "fertilizer": ["fertilizer", "soil", "general"],
    "irrigation": ["irrigation", "weather", "general"],
    "market":     ["market"],
    "yield":      ["seed", "general"],          # yield/estimation queries
    "soil":       ["soil", "fertilizer", "general"],
    "seed":       ["seed", "general"],
    "scheme":     ["scheme", "market"],
    "general":    ["general", "seed", "fertilizer"],
}

# Keyword sets for intent detection — used in farming_agent.detect_intent()
INTENT_KEYWORDS: dict[str, frozenset[str]] = {
    "weather": frozenset({
        "weather", "temperature", "forecast", "rain", "rainfall", "humidity",
        "sunny", "climate", "wind", "storm", "monsoon", "cloud", "hot", "cold",
    }),
    "disease": frozenset({
        "disease", "pest", "insect", "fungal", "virus", "blight", "blast",
        "rot", "mold", "mould", "rust", "wilt", "spot", "spots", "lesion",
        "yellowing", "browning", "holes", "larvae", "larva", "caterpillar",
        "aphid", "thrip", "whitefly", "hopper", "bollworm", "symptom",
        "infected", "infection", "attack", "damage", "yellow", "leaves",
    }),
    "spraying": frozenset({
        "spray", "spraying", "pesticide", "insecticide", "fungicide",
        "herbicide", "weedicide", "chemical", "neem", "dose", "ml",
        "spray today", "when spray", "can spray",
    }),
    "fertilizer": frozenset({
        "fertilizer", "fertilizers", "urea", "dap", "npk", "nitrogen",
        "phosphorus", "potassium", "potash", "manure", "compost",
        "vermicompost", "fym", "micronutrient", "zinc", "boron", "dose",
        "how much urea", "how much dap", "basal", "topdress",
    }),
    "irrigation": frozenset({
        "irrigation", "irrigate", "watering", "water", "drip", "sprinkler",
        "flood", "furrow", "moisture", "drought", "stress", "when water",
        "how much water",
    }),
    "market": frozenset({
        "price", "prices", "rate", "rates", "cost", "msp", "market", "mandi",
        "quintal", "sell", "selling", "buy", "buying", "rupee", "₹",
        "worth", "value", "profit", "income", "earn", "today price",
        "current price", "latest price", "how much",
    }),
    "yield": frozenset({
        "yield", "production", "harvest", "output", "ton", "tonnes", "kg",
        "per acre", "per hectare", "estimation", "estimate", "expected",
        "how much produce", "productivity",
    }),
    "soil": frozenset({
        "soil", "ph", "acidic", "alkaline", "saline", "organic", "carbon",
        "texture", "clay", "sandy", "loam", "black soil", "red soil",
        "soil test", "soil health",
    }),
    "seed": frozenset({
        "seed", "seeds", "variety", "hybrid", "sowing", "nursery",
        "seedling", "transplant", "germination", "spacing", "seed rate",
        "which variety", "best variety", "when sow", "sow",
    }),
    "scheme": frozenset({
        "scheme", "subsidy", "loan", "kcc", "kisan", "pm-kisan", "pmkisan",
        "rythu", "bandhu", "bima", "credit", "pmksy", "pmfby", "insurance",
        "enam", "government", "free", "apply",
    }),
}


# ─────────────────────────────────────────────────────────────────────────────
# MSP 2024-25 RATES  (CACP official)
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
# CHUNK METADATA SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

CHUNK_CATEGORIES = Literal[
    "disease",
    "fertilizer",
    "irrigation",
    "market",
    "weather",
    "soil",
    "seed",
    "scheme",
    "general",
]

CHUNK_SEASONS = Literal["kharif", "rabi", "zaid", "perennial", "all"]


@dataclass
class ChunkMetadata:
    crop:     str = "all"
    category: str = "general"
    language: str = "en"
    season:   str = "all"
    source:   str = ""
    page:     int = 0

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
        crop:     str | None = None,
        category: str | None = None,
        language: str | None = None,
        season:   str | None = None,
    ) -> dict:
        f: dict = {}
        if crop:     f["crop"]     = crop
        if category: f["category"] = category
        if language and language != "en":
            f["language"] = {"$in": [language, "all"]}
        if season and season != "all":
            f["season"] = {"$in": [season, "all"]}
        return f


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — BASE RULES + LANGUAGE WRAPPERS
#
# ✅ FIX 2: CRITICAL LIVE-DATA PRIORITY RULES added as the first block.
#           These override any knowledge-base values for prices / MSP.
# ─────────────────────────────────────────────────────────────────────────────

_BASE_RULES: str = """\
═══════════════════════════════════════════════════════
CRITICAL RULES — KNOWLEDGE PRIORITY  (read first, always)
═══════════════════════════════════════════════════════
1. LIVE DATA ALWAYS WINS.
   If REAL-TIME MANDI PRICES or REAL-TIME WEATHER are provided in this
   prompt, they are the ONLY source of truth for prices and weather.
   The knowledge base may contain MSP or price figures — IGNORE THEM
   completely if live data is present. Never mix old and new values.

2. NEVER USE OUTDATED MSP.
   The knowledge base contains MSP values for reference only.
   If live mandi prices are given, use those exact ₹ figures.
   If only MSP is available (no live feed), state clearly:
   "This is the government MSP — actual mandi price may differ."

3. NO PRICE MIXING.
   Never combine a live price from one source with an MSP from the
   knowledge base in the same sentence as if they are comparable.
   State each figure's source and date explicitly.
═══════════════════════════════════════════════════════

YOUR JOB:
Use the REAL-TIME DATA (live mandi prices, live weather) and REFERENCE
KNOWLEDGE provided to answer the farmer's question with exact numbers.

PRICES:
- Use ONLY the live mandi figures given. Never guess or substitute.
- State market name, state, and date with every price.
- Show price range when multiple markets are listed; highlight the nearest.
- Always compare today's mandi rate to the Govt MSP.
- Never give vague ranges — use exact ₹ figures.

WEATHER:
- Weather data is injected ONLY when relevant to the query (spraying,
  irrigation, disease management, or explicit weather questions).
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
            "Showing Govt MSP as reference only — actual mandi price may differ."
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
            "⚠ लाइव मंडी डेटा अभी उपलब्ध नहीं है। "
            "सरकारी MSP केवल संदर्भ के रूप में दिखाया जा रहा है — वास्तविक मंडी भाव अलग हो सकता है।"
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
            "ప్రభుత్వ MSPని సూచనగా మాత్రమే చూపిస్తున్నాం — వాస్తవ మండి ధర వేరుగా ఉండవచ్చు."
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
# CONVERSATION MEMORY
# ─────────────────────────────────────────────────────────────────────────────

Role = Literal["user", "assistant"]


@dataclass
class Turn:
    role:      Role
    content:   str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_llm_message(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationMemory:
    lang:            str = "en"
    max_turns:       int = 10
    summarise_every: int = 6

    _turns:               list[Turn] = field(default_factory=list, init=False)
    _summary:             str        = field(default="", init=False)
    _turns_since_summary: int        = field(default=0, init=False)

    detected_crop:     str | None = field(default=None, init=False)
    detected_location: str | None = field(default=None, init=False)
    detected_season:   str | None = field(default=None, init=False)

    def add_turn(self, role: Role, content: str) -> None:
        self._turns.append(Turn(role=role, content=content))
        self._turns_since_summary += 1
        if len(self._turns) > self.max_turns:
            self._turns = self._turns[-self.max_turns:]

    def should_summarise(self) -> bool:
        return self._turns_since_summary >= self.summarise_every

    def summary_prompt(self) -> str:
        return get_message(self.lang, "memory_summary_prompt")

    def apply_summary(self, summary_text: str) -> None:
        self._summary = summary_text
        self._turns_since_summary = 0
        self._turns = self._turns[-2:]

    def build_context(self) -> str:
        parts: list[str] = []
        header = get_message(self.lang, "memory_context_header")
        parts.append(header)
        if self._summary:
            parts.append(f"Summary: {self._summary}\n")
        for turn in self._turns:
            parts.append(f"{turn.role}: {turn.content}")
        return "\n".join(parts)

    def to_llm_messages(self) -> list[dict[str, str]]:
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
# SETTINGS
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
    groq_model:      str   = "llama-3.3-70b-versatile"   # ✅ upgraded model
    gemini_api_key:  str   = ""
    gemini_model:    str   = "gemini-2.0-flash"
    llm_temperature: float = 0.3

    # ── Live data ─────────────────────────────────────────────────────────────
    data_gov_api_key:    str   = ""
    agmarknet_base_url:  str   = (
        "https://api.data.gov.in/resource/"
        "9ef84268-d588-465a-a308-a864a43d0070"
    )
    api_timeout_seconds: float = 9.0

    # ── Default location ──────────────────────────────────────────────────────
    default_lat:           float = 17.385
    default_lon:           float = 78.4867
    default_location_name: str   = "Hyderabad, Telangana"

    # ── Default language ──────────────────────────────────────────────────────
    default_language: str = "en"

    # ── Weather thresholds ────────────────────────────────────────────────────
    rain_spray_block_pct:   float = 60.0
    rain_spray_caution_pct: float = 40.0
    wind_spray_block_kmh:   float = 25.0
    uv_spray_caution:       float = 8.0
    heat_stress_temp_c:     float = 40.0

    # ── RAG / retrieval ───────────────────────────────────────────────────────
    top_k_chunks:        int = 4
    max_response_tokens: int = 1024

    # ── Conversation memory ───────────────────────────────────────────────────
    memory_max_turns:       int = 10
    memory_summarise_every: int = 6

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
        return get_message(lang, key)

    def system_prompt(self, lang: str) -> str:
        return get_system_prompt(lang)

    def new_memory(self, lang: str | None = None) -> ConversationMemory:
        return ConversationMemory(
            lang=lang or self.default_language,
            max_turns=self.memory_max_turns,
            summarise_every=self.memory_summarise_every,
        )


settings = Settings()