"""
farming_agent.py
────────────────
Dual-LLM Architecture:
  ┌─────────────────────────────────────────────────────┐
  │  GROQ  (llama-3.1-8b-instant)                       │
  │  → Text Q&A, chat, recommendations, market advice   │
  │  → 14,400 req/day free tier                         │
  ├─────────────────────────────────────────────────────┤
  │  GEMINI  (gemini-2.0-flash)                         │
  │  → Image understanding, disease detection from pics │
  │  → Multimodal / OCR tasks                           │
  └─────────────────────────────────────────────────────┘

Pipeline per chat turn:
  user message (any language)
       │
       ▼
  language_detector  →  detect lang
       │
       ▼
  translator         →  translate to English
       │
       ▼
  rag_pipeline       →  retrieve relevant chunks
       │
       ▼
  [image?] → Gemini  │  [text only] → Groq
       │                      │
       └──────────┬───────────┘
                  ▼
          answer in English
                  │
                  ▼
  translator  →  translate back to user's language
                  │
                  ▼
  response JSON  →  { response, detected_language, agent_type, sources }
"""

from __future__ import annotations

import logging
import io
from dataclasses import dataclass
from PIL import Image

from chat.config import settings, LANGUAGE_MAP
from chat.language_detector import detect_language
from chat.translator import to_english, from_english
from chat.rag_pipeline import retrieve, format_context, get_agent_from_chunks

logger = logging.getLogger(__name__)


# =============================================================================
# GROQ CLIENT  — text chat, Q&A, recommendations
# =============================================================================
_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — text responses will be disabled.")
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=settings.groq_api_key)
        logger.info("[LLM] Groq client ready: %s", settings.groq_model)
        return _groq_client
    except Exception as e:
        logger.error("Failed to initialize Groq client: %s", e)
        return None


def _call_groq(prompt: str) -> str:
    """Call Groq for pure text responses."""
    client = _get_groq_client()
    if client is None:
        return (
            "Advisory service is currently unavailable (Groq API key not configured). "
            "Please contact your local Krishi Vigyan Kendra for assistance."
        )
    try:
        chat_completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=settings.max_response_tokens,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Groq API error: %s", exc)
        return (
            "I encountered an issue generating your answer. "
            "Please try again or contact your local KVK for assistance."
        )


# =============================================================================
# GEMINI CLIENT  — image understanding, multimodal
# =============================================================================
_gemini_model = None

def _get_gemini_model():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — image analysis will be disabled.")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=settings.max_response_tokens,
                temperature=0.3,
            ),
        )
        logger.info("[LLM] Gemini client ready: %s", settings.gemini_model)
        return _gemini_model
    except Exception as e:
        logger.error("Failed to initialize Gemini model: %s", e)
        return None


def _call_gemini_with_image(prompt: str, pil_image: Image.Image) -> str:
    """Call Gemini with an image — used ONLY when image is present."""
    model = _get_gemini_model()
    if model is None:
        # Fallback: try Groq with text-only prompt if Gemini unavailable
        logger.warning("Gemini unavailable for image — falling back to Groq text-only")
        return _call_groq(prompt)
    try:
        response = model.generate_content([prompt, pil_image])
        return response.text.strip()
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        # Fallback to Groq text-only on Gemini failure
        logger.warning("Gemini failed — falling back to Groq text-only")
        return _call_groq(prompt)


# =============================================================================
# SYSTEM PROMPT  (shared across both LLMs)
# =============================================================================
SYSTEM_PROMPT = """You are KrishiMitra, an expert AI agricultural advisor for Indian farmers.

Rules:
1. Prioritize using the provided KNOWLEDGE BASE CONTEXT and CNN DISEASE CLASSIFIER TOP SUGGESTIONS (if present). Base your response directly and strictly on the closest matching crop and symptoms found in them.
2. If an image is uploaded and the visual symptoms clearly contradict the CNN predictions, ignore the CNN suggestions and diagnose based on the image content and your agricultural expertise.
3. If the CNN detector does not identify a disease, analyze the image carefully to identify symptoms, pests, or nutrient deficiencies.
4. If the farmer asks for weather, temperature, or forecast information, provide real-time data using reliable sources (Open-Meteo).
5. Formatting & Price Rules (CRITICAL):
   - Always use clean, standard Markdown.
   - Use double newlines (\\n\\n) to separate paragraphs and sections.
   - Format lists as bullet points ('* ' or '- ') on separate lines.
   - Use bold (**text**) for headers or key terms.
   - Always include exact price details with ₹ symbol, numeric values, and units (/quintal, /acre).
6. If a question is completely unrelated to agriculture:
   - Politely decline, stating you are KrishiMitra and only assist with agricultural queries.
7. General guidelines:
   - Give specific quantities, doses, and timelines where available.
   - Keep answers concise, clear, and farmer-friendly.
   - Never recommend banned pesticides (Monocrotophos, Endosulfan).
   - Language: Always respond in clear, simple English — translation is handled separately.
"""


# =============================================================================
# RESPONSE DATACLASS
# =============================================================================
@dataclass
class AgentResponse:
    response: str
    detected_language: str
    language_name: str
    agent_type: str
    sources: list[str]
    english_query: str
    english_response: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _build_prompt(english_query: str, context: str, cnn_info: str = "") -> str:
    prompt_parts = []
    if cnn_info:
        prompt_parts.append(cnn_info)
    prompt_parts.append(f"KNOWLEDGE BASE CONTEXT:\n{context}")
    prompt_parts.append(f"FARMER'S QUESTION: {english_query}")
    prompt_parts.append("ANSWER:")
    return "\n\n".join(prompt_parts)


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error("Failed to extract text from PDF: %s", e)
        return ""


def _extract_text_from_txt(txt_bytes: bytes) -> str:
    try:
        return txt_bytes.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        logger.error("Failed to decode text bytes: %s", e)
        return ""


def _get_cnn_prediction(pil_image: Image.Image) -> dict | None:
    try:
        from inference import predict_from_pil
        return predict_from_pil(pil_image)
    except Exception as e:
        logger.error("CNN prediction error: %s", e)
        return None


import httpx
import urllib.parse
from typing import Tuple


def _is_weather_query(query: str) -> bool:
    keywords = ["weather", "temperature", "forecast", "rain", "humidity", "sunny", "climate"]
    return any(k in query.lower() for k in keywords)


async def _fetch_weather(location: str) -> Tuple[float, float, str]:
    clean_name = location.split(",")[0].strip()
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_name)}&count=1&language=en&format=json"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, timeout=10.0)
        data = res.json()
        if not data.get("results"):
            lat, lon = 13.13768, 78.12999
            matched = location
        else:
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
            matched = f"{data['results'][0]['name']}, {data['results'][0].get('admin1', data['results'][0].get('country'))}"

    forecast_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&timezone=auto"
    )
    async with httpx.AsyncClient() as client:
        f_res = await client.get(forecast_url, timeout=10.0)
        f_data = f_res.json()
        daily = f_data.get("daily", {})
        if daily:
            t_max = daily.get("temperature_2m_max", [None])[0]
            t_min = daily.get("temperature_2m_min", [None])[0]
            rain_prob = daily.get("precipitation_probability_max", [0])[0]
            avg_temp = (t_max + t_min) / 2 if t_max is not None and t_min is not None else None
            return avg_temp, rain_prob, matched
    return None, None, matched


_GREETING_KEYWORDS = {
    "hello", "hi", "hey", "namaste", "namaskar", "namaskaram", "pranam",
    "good morning", "good afternoon", "good evening", "vanakkam", "yo", "sup"
}

_AGRI_KEYWORDS = {
    "farm", "farming", "farmer", "farmers", "agriculture", "agricultural", "agri",
    "crop", "crops", "cultivate", "cultivation", "sow", "sowing", "harvest", "harvesting",
    "soil", "fertilizer", "fertilizers", "manure", "compost", "vermicompost", "fym",
    "nitrogen", "phosphorus", "potassium", "potash", "urea", "npk",
    "paddy", "rice", "wheat", "maize", "corn", "cotton", "groundnut", "peanut",
    "chilli", "tomato", "onion", "potato", "brinjal", "eggplant", "cabbage",
    "cauliflower", "banana", "soybean", "pulse", "pulses", "gram", "chana",
    "tur", "arhar", "moong", "urad", "mustard", "rapeseed", "sesame", "sunflower",
    "barley", "ragi", "jowar", "sorghum", "bajra", "millet",
    "seed", "seeds", "seedling", "nursery",
    "irrigation", "irrigate", "water", "watering", "drip", "sprinkler",
    "monsoon", "rain", "rainfall", "weather", "temperature", "forecast", "climate",
    "pest", "pests", "insect", "bug", "worm", "bollworm", "hopper", "aphid",
    "thrips", "mite", "whitefly", "caterpillar",
    "disease", "diseases", "fungus", "fungal", "virus", "viral", "bacteria",
    "bacterial", "blight", "blast", "rot", "mold", "rust", "mosaic", "wilt", "mildew",
    "pesticide", "insecticide", "fungicide", "herbicide", "weedicide", "weed",
    "price", "prices", "cost", "msp", "market", "mandi", "rate", "quintal",
    "rupee", "rupees", "rs", "₹",
    "subsidy", "scheme", "loan", "kisan", "krishi", "rythu", "bandhu",
    "bima", "credit", "kcc", "pmksy", "pmfby", "pmkisan",
    "yield", "production", "variety", "hybrid",
}


def _is_greeting(text: str) -> bool:
    import re
    cleaned = re.sub(r'[^\w\s]', '', text.lower().strip())
    if cleaned in _GREETING_KEYWORDS:
        return True
    words = cleaned.split()
    return len(words) <= 2 and any(w in _GREETING_KEYWORDS for w in words)


def _is_agriculture_query(text: str) -> bool:
    import re
    tokens = set(re.findall(r'\b\w+\b', text.lower()))
    if tokens.intersection(_AGRI_KEYWORDS):
        return True
    for kw in ["agri", "krishi", "rythu", "kisan", "mandi", "weather", "irrigate", "fertiliz"]:
        if kw in text.lower():
            return True
    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
async def process_query(
    user_message: str,
    image_bytes: bytes | None = None,
    file_bytes: bytes | None = None,
    file_name: str | None = None,
    override_lang: str = "",
) -> AgentResponse:
    """
    Full pipeline:
      - Images   → Gemini (multimodal understanding)
      - Text     → Groq   (fast, free, accurate)
    """

    # ── 1. Detect language ────────────────────────────────────────────────────
    lang_code, lang_name = detect_language(user_message)
    logger.info("Detected language: %s (%s)", lang_name, lang_code)

    # ── 2. Translate to English for RAG ───────────────────────────────────────
    english_query = to_english(user_message, lang_code) if lang_code != "en" else user_message
    logger.debug("Translated query: %s", english_query)

    # Resolve output language
    output_lang = lang_code if lang_code in ("te", "hi") else (override_lang if override_lang in ("te", "hi") else lang_code)

    # ── 2b. Agriculture guard ─────────────────────────────────────────────────
    if not (image_bytes or file_bytes) and not _is_greeting(english_query) and not _is_agriculture_query(english_query):
        reject_msg_en = (
            "I am KrishiMitra, your AI agricultural advisor. "
            "I can only assist with agriculture, farming, and crop-related queries."
        )
        reject_translated = from_english(reject_msg_en, output_lang) if output_lang != "en" else reject_msg_en
        return AgentResponse(
            response=reject_translated,
            detected_language=lang_code,
            language_name=lang_name,
            agent_type="general",
            sources=[],
            english_query=english_query,
            english_response=reject_msg_en,
        )

    # ── 3. Document extraction ────────────────────────────────────────────────
    extracted_text = ""
    if file_bytes and file_name:
        if file_name.lower().endswith(".pdf"):
            extracted_text = _extract_text_from_pdf(file_bytes)
        elif file_name.lower().endswith(".txt"):
            extracted_text = _extract_text_from_txt(file_bytes)
        if extracted_text:
            logger.info("Extracted %d chars from %s", len(extracted_text), file_name)

    # ── 4. Image processing — CNN + Gemini ───────────────────────────────────
    pil_image    = None
    cnn_info     = ""
    cnn_agent    = None
    cnn_sources  = []

    if image_bytes:
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            cnn_result = _get_cnn_prediction(pil_image)
            if cnn_result:
                parts = []
                for item in cnn_result.get("top_k", []):
                    if item["confidence"] >= 10.0 or item["rank"] == 1:
                        from disease_info import get_disease_info
                        details  = get_disease_info(item["class"])
                        p_parts  = item["class"].split("___")
                        p_plant  = p_parts[0].replace("_", " ").strip() if p_parts else "Crop"
                        p_cond   = p_parts[1].replace("_", " ").strip() if len(p_parts) > 1 else "Condition"
                        parts.append(
                            f"Rank {item['rank']}: {p_plant} — {p_cond} "
                            f"(Confidence: {item['confidence']}%)\n"
                            f"  Severity: {details.get('severity', 'moderate')}\n"
                            f"  Cause: {details.get('cause', 'N/A')}\n"
                            f"  Organic: {details.get('organic', 'N/A')}\n"
                            f"  Chemical: {details.get('chemical', 'N/A')}\n"
                            f"  Prevention: {details.get('prevention', 'N/A')}"
                        )
                if parts:
                    cnn_info = (
                        "CNN DISEASE CLASSIFIER TOP SUGGESTIONS:\n"
                        + "\n\n".join(parts)
                        + "\n\nInstructions: Analyze the uploaded image, match visual symptoms to the "
                          "suggestions above, and select the most accurate disease. If suggestions "
                          "don't fit the image, use your general expertise."
                    )
                    cnn_agent   = "disease"
                    cnn_sources = ["AgriGPT Disease Diagnosis Database 2026"]
        except Exception as e:
            logger.error("Image/CNN processing error: %s", e)

    # ── 5. Weather + RAG retrieval ────────────────────────────────────────────
    weather_context = ""
    if _is_weather_query(english_query):
        try:
            avg_temp, rain_prob, matched_loc = await _fetch_weather(english_query)
            if avg_temp is not None:
                weather_context = (
                    f"Live Weather for {matched_loc}:\n"
                    f"- Average temperature: {avg_temp:.1f}°C\n"
                    f"- Precipitation probability: {rain_prob}%\n"
                )
        except Exception as e:
            logger.error("Weather fetch failed: %s", e)

    chunks     = retrieve(english_query)
    context    = format_context(chunks)
    if weather_context:
        context = weather_context + "\n\n" + context

    agent_type = cnn_agent or get_agent_from_chunks(chunks)
    sources    = list({c["source"] for c in chunks})
    if cnn_sources:
        sources = list(set(sources + cnn_sources))
    if extracted_text:
        context = f"[Document Content ({file_name})]:\n{extracted_text}\n\n" + context

    # ── 6. LLM call — Gemini for images, Groq for text ───────────────────────
    prompt = _build_prompt(english_query, context, cnn_info)

    if pil_image is not None:
        # IMAGE present → Gemini (multimodal)
        logger.info("[Router] Image detected → using Gemini (%s)", settings.gemini_model)
        english_answer = _call_gemini_with_image(prompt, pil_image)
    else:
        # TEXT only → Groq (fast + free)
        logger.info("[Router] Text only → using Groq (%s)", settings.groq_model)
        english_answer = _call_groq(prompt)

    # ── 7. Translate answer back ──────────────────────────────────────────────
    final_answer = from_english(english_answer, output_lang) if output_lang != "en" else english_answer

    return AgentResponse(
        response=final_answer,
        detected_language=lang_code,
        language_name=lang_name,
        agent_type=agent_type,
        sources=sources,
        english_query=english_query,
        english_response=english_answer,
    )