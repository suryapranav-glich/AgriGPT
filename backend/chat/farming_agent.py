"""farming_agent.py
────────────────────────────────────────────────────────────────────────────
Architecture:
  GROQ   — text Q&A, market advice, general farming
  GEMINI — image / disease detection only

Prompt sent to Groq every turn:
  [SYSTEM PROMPT]            ← language-specific, from config
  [CONVERSATION MEMORY]      ← ✅ NEW — sliding window + summary
  [CNN DISEASE INFO]         ← only when image uploaded
  [LIVE MANDI PRICES]        ← real-time AgMarkNet fetch
  [LIVE WEATHER]             ← real-time Open-Meteo fetch
  [UPLOADED DOCUMENT]        ← only when file attached
  [RAG KNOWLEDGE BASE]       ← background agronomy facts
  [FARMER'S QUESTION]

Memory lifecycle (per user session):
  • Caller creates one ConversationMemory via settings.new_memory(lang)
  • Passes it into every process_query() call for that session
  • Memory auto-summarises after settings.memory_summarise_every new turns
  • Caller persists the memory object between requests (e.g. in session state)

No Anthropic API is used anywhere in this file.
All strings configurable via settings / .env — nothing hardcoded.
────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import io
import logging
import re
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime

import httpx
from PIL import Image

from chat.config import ConversationMemory, settings
from chat.language_detector import detect_language
from chat.translator import from_english, to_english
from chat.rag_pipeline import format_context, get_agent_from_chunks, retrieve

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────────────────────

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if not settings.groq_api_key:
        logger.warning("[Groq] GROQ_API_KEY not configured.")
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=settings.groq_api_key)
        logger.info("[Groq] Client ready — model: %s", settings.groq_model)
        return _groq_client
    except Exception as exc:
        logger.error("[Groq] Init failed: %s", exc)
        return None


def _call_groq(
    user_prompt:  str,
    system_prompt: str,
    memory: ConversationMemory | None = None,
) -> str:
    """
    Call Groq with a full message array.

    Message order sent to the API:
      1. system   — language-specific KrishiMitra system prompt
      2. system   — conversation memory summary (if one exists)
      3. …turns…  — recent raw turns from the sliding window
      4. user     — the assembled prompt for this turn

    Using a second system message for the summary keeps it authoritative
    without inflating the visible conversation history.
    """
    client = _get_groq_client()
    if client is None:
        return settings.message(
            memory.lang if memory else "en", "llm_unavailable"
        )

    # Build message array
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    # Inject memory
    if memory and memory.turn_count > 0:
        # Summary goes in as a second system message — highest authority
        if memory._summary:
            messages.append({
                "role":    "system",
                "content": (
                    "CONVERSATION SUMMARY (what has been established so far):\n"
                    + memory._summary
                ),
            })
        # Recent raw turns (already trimmed to max_turns inside ConversationMemory)
        messages.extend(memory.to_llm_messages())

    # Current user prompt (with RAG / live data already embedded)
    messages.append({"role": "user", "content": user_prompt})

    try:
        completion = client.chat.completions.create(
            model       = settings.groq_model,
            messages    = messages,
            temperature = settings.llm_temperature,
            max_tokens  = settings.max_response_tokens,
        )
        return completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("[Groq] API error: %s", exc)
        return settings.message(
            memory.lang if memory else "en", "llm_error"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY SUMMARISATION
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_summarise(memory: ConversationMemory, system_prompt: str) -> None:
    """
    If the memory window is due for compression, call Groq with the
    summarisation prompt and apply the result back to the memory object.

    This is called AFTER the assistant turn is stored, so the summary
    captures the full exchange.
    """
    if not memory.should_summarise():
        return

    summary_request = (
        memory.summary_prompt()           # lang-specific instruction
        + "\n\nConversation to summarise:\n"
        + memory.build_context()          # full current window
    )

    summary = _call_groq(
        user_prompt   = summary_request,
        system_prompt = system_prompt,
        memory        = None,             # no memory for the meta-call
    )

    memory.apply_summary(summary)
    logger.info(
        "[Memory] Summarised after %d turns — %d chars",
        memory.summarise_every,
        len(summary),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI CLIENT  (image analysis only)
# ─────────────────────────────────────────────────────────────────────────────

_gemini_model = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    if not settings.gemini_api_key:
        logger.warning("[Gemini] API key not configured — image analysis disabled.")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=settings.max_response_tokens,
                temperature=settings.llm_temperature,
            ),
        )
        logger.info("[Gemini] Client ready — model: %s", settings.gemini_model)
        return _gemini_model
    except Exception as exc:
        logger.error("[Gemini] Init failed: %s", exc)
        return None


def _call_gemini_with_image(
    prompt:    str,
    pil_image: Image.Image,
    memory:    ConversationMemory | None = None,
    system_prompt: str = "",
) -> str:
    """
    Call Gemini for image-based disease detection.
    Falls back to Groq (text-only) if Gemini is unavailable.
    Memory context is prepended to the prompt text since Gemini's
    generativeai SDK does not accept a separate system-messages array.
    """
    model = _get_gemini_model()
    if model is None:
        logger.warning("[Gemini] Unavailable — falling back to Groq (text-only).")
        return _call_groq(prompt, system_prompt, memory)

    # Prepend memory context to the text prompt so Gemini has continuity
    full_prompt = prompt
    if memory and memory.turn_count > 0:
        ctx = memory.build_context()
        full_prompt = ctx + "\n\n" + prompt

    try:
        response = model.generate_content([full_prompt, pil_image])
        return response.text.strip()
    except Exception as exc:
        logger.error("[Gemini] API error: %s — falling back to Groq.", exc)
        return _call_groq(prompt, system_prompt, memory)


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentResponse:
    response:          str
    detected_language: str
    language_name:     str
    agent_type:        str
    sources:           list[str]
    english_query:     str
    english_response:  str
    # Memory is returned so the caller can persist it between requests
    memory:            ConversationMemory | None = None


# ─────────────────────────────────────────────────────────────────────────────
# LIVE MANDI PRICES  — AgMarkNet / data.gov.in
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_live_prices(crop_key: str, lang: str = "en") -> str:
    """
    Fetch real-time mandi arrivals from AgMarkNet (data.gov.in).
    Returns a formatted block for injection into the LLM prompt.
    Falls back to MSP-only text when the API returns nothing.
    """
    commodity = settings.agmarknet_crop_map.get(
        crop_key.lower(), crop_key.capitalize()
    )
    today_str = date.today().strftime("%d %b %Y")
    base_url  = settings.agmarknet_base_url
    api_key   = settings.data_gov_api_key

    records: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
            # Attempt 1 — exact AgMarkNet commodity name
            url1 = (
                f"{base_url}?api-key={api_key}&format=json&limit=25"
                f"&filters[commodity]={urllib.parse.quote(commodity)}"
            )
            records = (await client.get(url1)).json().get("records", [])

            # Attempt 2 — capitalised crop key (broader match)
            if not records:
                url2 = (
                    f"{base_url}?api-key={api_key}&format=json&limit=25"
                    f"&filters[commodity]={urllib.parse.quote(crop_key.capitalize())}"
                )
                records = (await client.get(url2)).json().get("records", [])

    except Exception as exc:
        logger.warning(
            "[Price] AgMarkNet request failed for '%s': %s", commodity, exc
        )

    # Sort newest arrivals first
    if records:
        try:
            records.sort(
                key=lambda r: datetime.strptime(
                    r.get("arrival_date", "01/01/2000"), "%d/%m/%Y"
                ),
                reverse=True,
            )
        except Exception:
            pass

        lines = [
            f"LIVE MANDI PRICES — {commodity.upper()}",
            f"Source: AgMarkNet / data.gov.in  |  Fetched: {today_str}",
            "",
        ]
        seen: set[str] = set()
        for r in records[:12]:
            market = r.get("market",      "").strip()
            state  = r.get("state",       "").strip()
            modal  = r.get("modal_price", "N/A")
            min_p  = r.get("min_price",   "N/A")
            max_p  = r.get("max_price",   "N/A")
            arr_dt = r.get("arrival_date", today_str)
            dedup  = f"{market}|{state}"
            if dedup in seen:
                continue
            seen.add(dedup)
            lines.append(
                f"  • {market}, {state}"
                f"  →  Modal ₹{modal}/qtl"
                f"  (Min ₹{min_p} – Max ₹{max_p})"
                f"  [{arr_dt}]"
            )

        msp_line = _msp_line(crop_key)
        if msp_line:
            lines += ["", msp_line, settings.message(lang, "msp_below")]

        logger.info("[Price] %d records returned for %s", len(records), commodity)
        return "\n".join(lines)

    # Fallback — MSP only
    msp_line = _msp_line(crop_key)
    if msp_line:
        logger.warning(
            "[Price] No live data for %s — returning MSP fallback.", commodity
        )
        return (
            f"PRICE DATA — {commodity.upper()}  (as of {today_str})\n"
            f"{settings.message(lang, 'mandi_unavailable')}\n"
            f"{msp_line}\n"
            f"{settings.message(lang, 'mandi_check')}\n"
            f"{settings.message(lang, 'msp_below')}"
        )

    return ""


def _msp_line(crop_key: str) -> str:
    """Return a single formatted MSP string for crop_key, or empty string."""
    msp_data = settings.msp_rates.get(crop_key.lower(), {})
    if not msp_data:
        return ""
    parts = [
        f"₹{v}/qtl ({g})" if g else f"₹{v}/qtl"
        for g, v in msp_data.items()
    ]
    return f"Govt MSP {settings.msp_season}:  {'  |  '.join(parts)}"


# ─────────────────────────────────────────────────────────────────────────────
# LIVE WEATHER  — Open-Meteo (free, no API key)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_weather(location: str) -> str:
    """
    Fetch a 3-day farming-relevant forecast from Open-Meteo.
    Returns a formatted block for injection into the LLM prompt.
    """
    today_str  = date.today().strftime("%d %b %Y")
    clean_name = location.split(",")[0].strip()

    # Geocode
    lat   = settings.default_lat
    lon   = settings.default_lon
    place = settings.default_location_name

    try:
        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(clean_name)}&count=1&language=en&format=json"
        )
        async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
            geo = (await client.get(geo_url)).json()
            if geo.get("results"):
                r     = geo["results"][0]
                lat   = r["latitude"]
                lon   = r["longitude"]
                place = f"{r['name']}, {r.get('admin1', r.get('country', ''))}"
    except Exception as exc:
        logger.warning("[Weather] Geocoding failed for '%s': %s", location, exc)

    # Forecast
    try:
        wx_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,precipitation_probability_max,"
            f"windspeed_10m_max,uv_index_max"
            f"&timezone=auto&forecast_days=3"
        )
        async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
            wx    = (await client.get(wx_url)).json()
            daily = wx.get("daily", {})

            dates     = daily.get("time",                          [])
            t_max_l   = daily.get("temperature_2m_max",            [])
            t_min_l   = daily.get("temperature_2m_min",            [])
            rain_mm_l = daily.get("precipitation_sum",             [])
            rain_pr_l = daily.get("precipitation_probability_max", [])
            wind_l    = daily.get("windspeed_10m_max",             [])
            uv_l      = daily.get("uv_index_max",                  [])

            if not dates:
                return ""

            lines = [
                f"LIVE WEATHER FORECAST — {place}",
                f"Source: Open-Meteo  |  Fetched: {today_str}",
                "",
            ]

            day_labels = ["Today", "Tomorrow", "Day after tomorrow"]
            for i in range(min(3, len(dates))):
                def _v(lst, fmt="{:.0f}", idx=i):
                    return fmt.format(lst[idx]) if idx < len(lst) else "N/A"
                lines.append(
                    f"  {day_labels[i]} ({dates[i]}):  "
                    f"{_v(t_min_l)}–{_v(t_max_l)}°C,  "
                    f"Rain {_v(rain_pr_l)}% / {_v(rain_mm_l, '{:.1f}')}mm,  "
                    f"Wind {_v(wind_l)} km/h,  UV {_v(uv_l)}"
                )

            advisories = _weather_advisories(
                rain_prob          = rain_pr_l[0] if rain_pr_l else None,
                rain_prob_tomorrow = rain_pr_l[1] if len(rain_pr_l) > 1 else None,
                wind               = wind_l[0]    if wind_l    else None,
                uv                 = uv_l[0]      if uv_l      else None,
                t_max              = t_max_l[0]   if t_max_l   else None,
            )
            if advisories:
                lines += ["", "FARMING ADVISORIES:"] + [f"  {a}" for a in advisories]

            logger.info("[Weather] 3-day forecast fetched for %s", place)
            return "\n".join(lines)

    except Exception as exc:
        logger.warning("[Weather] Forecast fetch failed for '%s': %s", location, exc)
        return ""


def _weather_advisories(
    rain_prob:          float | None,
    rain_prob_tomorrow: float | None,
    wind:               float | None,
    uv:                 float | None,
    t_max:              float | None,
) -> list[str]:
    """Return plain-text farming advisory strings derived from numeric weather."""
    out: list[str] = []

    if rain_prob is not None:
        if rain_prob >= settings.rain_spray_block_pct:
            out.append(
                f"⚠ Rain probability {rain_prob:.0f}% today — do NOT spray; "
                "rain will wash chemicals off. Wait until clear."
            )
        elif rain_prob >= settings.rain_spray_caution_pct:
            out.append(
                f"⚠ Moderate rain chance ({rain_prob:.0f}%) — spray early morning "
                "only if urgent, otherwise wait."
            )

    if wind is not None and wind >= settings.wind_spray_block_kmh:
        out.append(
            f"⚠ Strong winds ({wind:.0f} km/h) — avoid foliar sprays; "
            "drift will waste chemical and damage nearby crops."
        )

    if uv is not None and uv >= settings.uv_spray_caution:
        out.append(
            f"⚠ Very high UV ({uv:.0f}) — spray before 9 AM or after 4 PM; "
            "chemicals degrade fast in intense sunlight."
        )

    if t_max is not None and t_max >= settings.heat_stress_temp_c:
        out.append(
            f"⚠ Extreme heat ({t_max:.0f}°C) — irrigate in the evening; "
            "avoid midday field work."
        )

    if rain_prob_tomorrow is not None and \
            rain_prob_tomorrow >= settings.rain_spray_block_pct:
        out.append(
            f"Tomorrow: high rain probability ({rain_prob_tomorrow:.0f}%) — "
            "complete any harvesting or spraying today if the crop is ready."
        )

    return out


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(
    english_query: str,
    rag_context:   str,
    live_prices:   str = "",
    live_weather:  str = "",
    cnn_info:      str = "",
    extracted_doc: str = "",
) -> str:
    """
    Assemble the user-turn message sent to the LLM, in strict priority order:

      1. CNN disease classifier  — image-based, highest confidence
      2. LIVE MANDI PRICES       — overrides any RAG price figures
      3. LIVE WEATHER            — drives today's field decisions
      4. UPLOADED DOCUMENT       — farmer-provided file content
      5. RAG KNOWLEDGE BASE      — background agronomy / scheme facts
      6. FARMER'S QUESTION       — what to answer

    NOTE: Conversation memory is NOT added here.
    It is injected separately in _call_groq() as earlier messages in the
    messages array, which is the correct place for it.
    """
    SEP = "━" * 50
    sections: list[str] = []

    if cnn_info:
        sections.append(
            f"{SEP}\nCNN DISEASE CLASSIFIER (image-based — highest confidence)\n"
            f"{SEP}\n{cnn_info}"
        )

    if live_prices:
        sections.append(
            f"{SEP}\nREAL-TIME MANDI PRICES\n{SEP}\n"
            "IMPORTANT: Use ONLY these figures. Ignore any price numbers in "
            "the knowledge base below — those may be outdated.\n\n"
            + live_prices
        )

    if live_weather:
        sections.append(
            f"{SEP}\nREAL-TIME WEATHER FORECAST\n{SEP}\n"
            "Use these exact conditions when giving today's field advice.\n\n"
            + live_weather
        )

    if extracted_doc:
        sections.append(
            f"{SEP}\nFARMER'S UPLOADED DOCUMENT\n{SEP}\n{extracted_doc}"
        )

    if rag_context:
        sections.append(
            f"{SEP}\nBACKGROUND KNOWLEDGE BASE\n{SEP}\n"
            "(Use for agronomy facts, doses, scheme details. "
            "Live prices above take precedence over any price figures here.)\n\n"
            + rag_context
        )

    sections.append(
        f"{SEP}\nFARMER'S QUESTION\n{SEP}\n"
        f"{english_query}\n\n"
        "Answer directly and conversationally. "
        "Where real-time prices or weather are provided above, use those exact "
        "numbers — state the market name, state, and date. "
        "Be specific, practical, and talk like a trusted advisor."
    )

    return "\n\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# QUERY CLASSIFIERS
# ─────────────────────────────────────────────────────────────────────────────

_WEATHER_KEYWORDS = frozenset({
    "weather", "temperature", "forecast", "rain", "rainfall", "humidity",
    "sunny", "climate", "wind", "storm", "monsoon", "cloud", "hot", "cold",
    "spray today", "irrigate today",
})

_PRICE_KEYWORDS = frozenset({
    "price", "prices", "rate", "rates", "cost", "msp", "market", "mandi",
    "quintal", "sell", "selling", "buy", "buying", "rupee", "₹",
    "worth", "value", "profit", "income", "earn",
    "today price", "current price", "latest price", "how much",
})

_GREETING_KEYWORDS = frozenset({
    "hello", "hi", "hey", "namaste", "namaskar", "namaskaram",
    "pranam", "good morning", "good afternoon", "good evening",
    "vanakkam", "yo", "sup",
})

_AGRI_KEYWORDS = frozenset({
    "farm", "farming", "farmer", "farmers", "agriculture", "agricultural",
    "agri", "crop", "crops", "cultivate", "cultivation", "sow", "sowing",
    "harvest", "harvesting", "soil", "fertilizer", "fertilizers", "manure",
    "compost", "vermicompost", "fym", "nitrogen", "phosphorus", "potassium",
    "potash", "urea", "npk", "paddy", "rice", "wheat", "maize", "corn",
    "cotton", "groundnut", "peanut", "chilli", "tomato", "onion", "potato",
    "brinjal", "eggplant", "cabbage", "cauliflower", "banana", "soybean",
    "pulse", "pulses", "gram", "chana", "tur", "arhar", "moong", "urad",
    "mustard", "rapeseed", "sesame", "sunflower", "barley", "ragi",
    "jowar", "sorghum", "bajra", "millet", "seed", "seeds", "seedling",
    "nursery", "irrigation", "irrigate", "water", "watering", "drip",
    "sprinkler", "monsoon", "rain", "rainfall", "weather", "temperature",
    "forecast", "climate", "pest", "pests", "insect", "bug", "worm",
    "bollworm", "hopper", "aphid", "thrips", "mite", "whitefly",
    "caterpillar", "disease", "diseases", "fungus", "fungal", "virus",
    "viral", "bacteria", "bacterial", "blight", "blast", "rot", "mold",
    "rust", "mosaic", "wilt", "mildew", "pesticide", "insecticide",
    "fungicide", "herbicide", "weedicide", "weed", "price", "prices",
    "cost", "msp", "market", "mandi", "rate", "quintal", "rupee",
    "rupees", "rs", "₹", "subsidy", "scheme", "loan", "kisan", "krishi",
    "rythu", "bandhu", "bima", "credit", "kcc", "pmksy", "pmfby",
    "pmkisan", "yield", "production", "variety", "hybrid", "grow",
    "growing", "plant", "planting", "transplant", "spray", "spraying",
    "apply", "application", "stage", "stages", "days", "week", "season",
})

# Ordered longest-first so "soybean" matches before "bean"
_KNOWN_CROPS_ORDERED = [
    "soybean", "sunflower", "groundnut", "sugarcane", "cauliflower",
    "paddy", "rice", "wheat", "cotton", "maize", "corn",
    "onion", "tomato", "potato", "chilli", "jowar", "bajra",
    "ragi", "tur", "arhar", "moong", "urad", "mustard",
    "banana", "mango", "brinjal", "cabbage",
]

_AGRI_SUBSTRINGS = (
    "agri", "krishi", "rythu", "kisan", "mandi", "weather",
    "irrigat", "fertiliz", "grow", "plant", "harvest", "spray", "crop",
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", text.lower()))


def _is_weather_query(query: str) -> bool:
    return bool(_tokens(query) & _WEATHER_KEYWORDS)


def _is_price_query(query: str) -> bool:
    return bool(_tokens(query) & _PRICE_KEYWORDS)


def _is_greeting(text: str) -> bool:
    cleaned = re.sub(r"[^\w\s]", "", text.lower().strip())
    if cleaned in _GREETING_KEYWORDS:
        return True
    words = cleaned.split()
    return len(words) <= 2 and bool(set(words) & _GREETING_KEYWORDS)


def _is_agriculture_query(text: str) -> bool:
    if _tokens(text) & _AGRI_KEYWORDS:
        return True
    tl = text.lower()
    return any(sub in tl for sub in _AGRI_SUBSTRINGS)


def _extract_crop(query: str) -> str | None:
    q = query.lower()
    for crop in _KNOWN_CROPS_ORDERED:
        if crop in q:
            return crop
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except Exception as exc:
        logger.error("[Doc] PDF extraction failed: %s", exc)
        return ""


def _extract_txt_text(txt_bytes: bytes) -> str:
    try:
        return txt_bytes.decode("utf-8", errors="ignore").strip()
    except Exception as exc:
        logger.error("[Doc] TXT decode failed: %s", exc)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# CNN HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _run_cnn(pil_image: Image.Image) -> tuple[str, str, list[str]]:
    """Returns (cnn_info_text, agent_type, sources).
    cnn_info_text is empty string if CNN is unavailable or returns nothing."""
    try:
        from inference import predict_from_pil
        result = predict_from_pil(pil_image)
    except Exception as exc:
        logger.error("[CNN] Prediction error: %s", exc)
        return "", "", []

    if not result:
        return "", "", []

    parts: list[str] = []
    for item in result.get("top_k", []):
        if item["confidence"] < 10.0 and item["rank"] != 1:
            continue
        try:
            from disease_info import get_disease_info
            details = get_disease_info(item["class"])
        except Exception:
            details = {}

        raw   = item["class"].split("___")
        plant = raw[0].replace("_", " ").strip() if raw        else "Crop"
        cond  = raw[1].replace("_", " ").strip() if len(raw) > 1 else "Condition"
        parts.append(
            f"Rank {item['rank']}: {plant} — {cond} "
            f"(Confidence: {item['confidence']:.1f}%)\n"
            f"  Severity:   {details.get('severity',   'moderate')}\n"
            f"  Cause:      {details.get('cause',      'N/A')}\n"
            f"  Organic:    {details.get('organic',    'N/A')}\n"
            f"  Chemical:   {details.get('chemical',   'N/A')}\n"
            f"  Prevention: {details.get('prevention', 'N/A')}"
        )

    if not parts:
        return "", "", []

    cnn_text = (
        "CNN DISEASE CLASSIFIER — TOP MATCHES:\n"
        + "\n\n".join(parts)
        + "\n\nMatch visual symptoms from the image to the suggestions above. "
          "Select the most accurate disease. If none fit, use your general expertise."
    )
    return cnn_text, "disease", [settings.cnn_source_label]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

async def process_query(
    user_message:  str,
    image_bytes:   bytes | None          = None,
    file_bytes:    bytes | None          = None,
    file_name:     str   | None          = None,
    override_lang: str                   = "",
    memory:        ConversationMemory | None = None,
) -> AgentResponse:
    """
    Full pipeline with conversation memory.

    Parameters
    ----------
    user_message  : Raw message from the farmer (any language).
    image_bytes   : Optional uploaded image (disease detection via Gemini).
    file_bytes    : Optional uploaded document (PDF or TXT).
    file_name     : Filename of the uploaded document (used to pick parser).
    override_lang : Force a specific output language (e.g. "te").
    memory        : ConversationMemory instance for this session.
                    Create once per session:  memory = settings.new_memory()
                    Pass it into every call — the pipeline mutates it in-place.

    Returns
    -------
    AgentResponse — includes the same memory object so stateless callers
    (e.g. FastAPI request handlers) can store it in session state.

    Memory lifecycle inside this function:
      Step  1 — user turn stored immediately
      Step 13 — assistant turn stored after LLM call
      Step 14 — summarisation triggered if window is full
    """

    # ── 1. Language detection ─────────────────────────────────────────────────
    lang_code, lang_name = detect_language(user_message)
    logger.info("[Lang] %s (%s)", lang_name, lang_code)

    # ── 2. Translate to English ───────────────────────────────────────────────
    english_query = (
        to_english(user_message, lang_code) if lang_code != "en" else user_message
    )
    logger.debug("[Query] %s", english_query)

    # Output language: detected lang takes priority; else override; else English
    output_lang = lang_code if lang_code != "en" else (override_lang or "en")

    # ── 3. Initialise or update memory ───────────────────────────────────────
    if memory is None:
        memory = settings.new_memory(lang=output_lang)
        logger.info("[Memory] New session started (lang=%s)", output_lang)
    else:
        # Keep memory's lang in sync with detected language
        memory.lang = output_lang

    # Update session context the agent has detected so far
    detected_crop_now = _extract_crop(english_query)
    if detected_crop_now:
        memory.detected_crop = detected_crop_now
    if _is_weather_query(english_query):
        # Best-effort location from the query itself; refine in step 7
        memory.detected_location = memory.detected_location or english_query

    # Store the user's raw message (original language — richer for summaries)
    memory.add_turn("user", user_message)

    # ── 4. Language-specific system prompt ───────────────────────────────────
    system_prompt = settings.system_prompt(output_lang)

    # ── 5. Non-agriculture guard ──────────────────────────────────────────────
    if (
        not (image_bytes or file_bytes)
        and not _is_greeting(english_query)
        and not _is_agriculture_query(english_query)
    ):
        reject_en  = settings.message(output_lang, "non_agri_reject")
        reject_out = (
            from_english(reject_en, output_lang)
            if output_lang != "en" else reject_en
        )
        # Still store the assistant turn so memory stays coherent
        memory.add_turn("assistant", reject_out)
        return AgentResponse(
            response          = reject_out,
            detected_language = lang_code,
            language_name     = lang_name,
            agent_type        = "general",
            sources           = [],
            english_query     = english_query,
            english_response  = reject_en,
            memory            = memory,
        )

    # ── 6. Document extraction ────────────────────────────────────────────────
    extracted_text = ""
    if file_bytes and file_name:
        fn = file_name.lower()
        if fn.endswith(".pdf"):
            extracted_text = _extract_pdf_text(file_bytes)
        elif fn.endswith(".txt"):
            extracted_text = _extract_txt_text(file_bytes)
        if extracted_text:
            logger.info("[Doc] %d chars from %s", len(extracted_text), file_name)

    # ── 7. Image → PIL + CNN ──────────────────────────────────────────────────
    pil_image    = None
    cnn_info     = ""
    cnn_agent: str | None = None
    cnn_sources: list[str] = []

    if image_bytes:
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            cnn_info, cnn_agent_raw, cnn_sources = _run_cnn(pil_image)
            cnn_agent = cnn_agent_raw or None
        except Exception as exc:
            logger.error("[Image] Processing error: %s", exc)

    # ── 8. Live weather ───────────────────────────────────────────────────────
    live_weather = ""
    if _is_weather_query(english_query):
        logger.info("[Weather] Fetching forecast")
        live_weather = await _fetch_weather(english_query)

    # ── 9. Live mandi prices ──────────────────────────────────────────────────
    live_prices   = ""
    detected_crop = memory.detected_crop or _extract_crop(english_query)
    if _is_price_query(english_query) and detected_crop:
        logger.info("[Price] Fetching for: %s", detected_crop)
        live_prices = await _fetch_live_prices(detected_crop, lang=output_lang)

    # ── 10. RAG ───────────────────────────────────────────────────────────────
    chunks      = retrieve(english_query)
    rag_context = format_context(chunks)

    # ── 11. Determine agent type + sources ────────────────────────────────────
    agent_type = cnn_agent or get_agent_from_chunks(chunks)
    if live_prices and not cnn_agent:
        agent_type = "market"

    sources: list[str] = list({c["source"] for c in chunks})
    if cnn_sources:
        sources = list(set(sources + cnn_sources))
    if live_prices:
        sources = list(set(sources + [settings.agmarknet_source_label]))
    if live_weather:
        sources = list(set(sources + [settings.openmeteo_source_label]))

    # ── 12. Build prompt (live data + RAG only; memory injected in _call_groq) ─
    prompt = _build_prompt(
        english_query = english_query,
        rag_context   = rag_context,
        live_prices   = live_prices,
        live_weather  = live_weather,
        cnn_info      = cnn_info,
        extracted_doc = extracted_text,
    )

    # ── 13. Call LLM ─────────────────────────────────────────────────────────
    if pil_image is not None:
        logger.info("[Router] Image → Gemini")
        english_answer = _call_gemini_with_image(
            prompt        = prompt,
            pil_image     = pil_image,
            memory        = memory,
            system_prompt = system_prompt,
        )
    else:
        logger.info("[Router] Text → Groq")
        english_answer = _call_groq(
            user_prompt   = prompt,
            system_prompt = system_prompt,
            memory        = memory,
        )

    # ── 14. Translate answer back ─────────────────────────────────────────────
    final_answer = (
        from_english(english_answer, output_lang)
        if output_lang != "en" else english_answer
    )

    # ── 15. Store assistant turn + trigger summarisation if needed ────────────
    memory.add_turn("assistant", final_answer)
    _maybe_summarise(memory, system_prompt)

    logger.info(
        "[Memory] Session: %d turns | summary: %s | crop: %s",
        memory.turn_count,
        "yes" if memory._summary else "no",
        memory.detected_crop or "unknown",
    )

    return AgentResponse(
        response          = final_answer,
        detected_language = lang_code,
        language_name     = lang_name,
        agent_type        = agent_type,
        sources           = sources,
        english_query     = english_query,
        english_response  = english_answer,
        memory            = memory,
    )