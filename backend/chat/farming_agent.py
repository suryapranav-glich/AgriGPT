"""
farming_agent.py
────────────────
Orchestrates the full pipeline for a single chat turn:

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
  Gemini LLM         →  generate answer in English
       │
       ▼
  translator         →  translate answer back to user's language
       │
       ▼
  response JSON      →  { response, detected_language, agent_type, sources }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
import io
import google.generativeai as genai  # type: ignore
from PIL import Image

from chat.config import settings, LANGUAGE_MAP
from chat.language_detector import detect_language
from chat.translator import to_english, from_english
from chat.rag_pipeline import retrieve, format_context, get_agent_from_chunks

logger = logging.getLogger(__name__)

# ── Gemini setup ──────────────────────────────────────────────────────────────
# We initialize the model on demand or when called so setting key works dynamically
_gemini = None

def _get_gemini_model():
    global _gemini
    if _gemini is not None:
        return _gemini
    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)
        _gemini = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=settings.max_response_tokens,
                temperature=0.3,    # lower = more factual for agricultural advice
            ),
        )

        return _gemini
    else:
        logger.warning("GEMINI_API_KEY not set — LLM responses will be disabled.")
        return None


SYSTEM_PROMPT = """You are KrishiMitra, an expert AI agricultural advisor for Indian farmers.

Rules:
1. Prioritize using the provided KNOWLEDGE BASE CONTEXT and CNN DISEASE CLASSIFIER TOP SUGGESTIONS (if present). Base your response directly and strictly on the closest matching crop and symptoms found in them. Compare the farmer's symptoms (e.g., spots, color, patches) with those in the suggestions and context.
2. **If an image is uploaded and the visual symptoms clearly contradict the CNN predictions, ignore the CNN suggestions and diagnose based on the image content and your agricultural expertise.**
3. If the CNN detector does not identify a disease, analyze the image carefully to identify symptoms, pests, or nutrient deficiencies, and combine it with your expertise to provide a correct, safe, and practical answer.
4. If the farmer asks for weather, temperature, or forecast information, provide real-time data using reliable sources (Open-Meteo) instead of static advice.
5. Formatting & Price Rules (CRITICAL):
   - Always use clean, standard Markdown.
   - Use double newlines (\\n\\n) to separate different paragraphs and sections. Never bundle everything into one block of text.
   - When presenting lists of recommendations (like treatments, prevention tips, symptoms), ALWAYS format them as bullet points (using '* ' or '- ') on separate lines.
   - Never output all list items inline within a single paragraph. Every list item MUST start on a new line with a bullet.
   - Use bold (**text**) for headers or key terms (like **Leaf Mold**, **Chemical Treatment:**) to make the text easily readable.
   - When discussing prices, market rates, or Minimum Support Prices (MSP), ALWAYS include the exact price details, numeric values, and units (e.g., '/quintal', '/acre') exactly as provided in the context, along with the Rupee symbol (₹). Format prices clearly in lists or markdown tables. Do not omit, simplify, or modify currency symbols or prices.
6. If a question is completely unrelated to agriculture (e.g., general history, sports, entertainment, general non-farming queries):
   - Politely decline to answer, stating that you are KrishiMitra and can only assist with agricultural and farming queries.
7. General guidelines:
   - Give specific quantities, doses, and timelines where available.
   - Keep answers concise, clear, and farmer-friendly (avoid jargon when possible).
   - Never recommend banned pesticides (e.g., Monocrotophos, Endosulfan).
   - Language: Always respond in clear, simple English — translation to the user's language is handled separately.
"""


@dataclass
class AgentResponse:
    response: str
    detected_language: str
    language_name: str
    agent_type: str
    sources: list[str]
    english_query: str
    english_response: str


def _build_prompt(english_query: str, context: str, cnn_info: str = "") -> str:
    prompt_parts = [SYSTEM_PROMPT]
    if cnn_info:
        prompt_parts.append(cnn_info)
    prompt_parts.append(f"KNOWLEDGE BASE CONTEXT:\n{context}")
    prompt_parts.append(f"FARMER'S QUESTION: {english_query}")
    prompt_parts.append("ANSWER:")
    return "\n\n".join(prompt_parts)


def _call_gemini(prompt: str, pil_image: Image.Image | None = None) -> str:
    model = _get_gemini_model()
    if model is None:
        return (
            "Advisory service is currently unavailable (API key not configured). "
            "Please contact your local Krishi Vigyan Kendra for assistance."
        )
    try:
        if pil_image:
            response = model.generate_content([prompt, pil_image])
        else:
            response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return (
            "I encountered an issue generating your answer. "
            "Please try again or contact your local KVK for assistance."
        )


def _get_cnn_prediction(pil_image: Image.Image) -> dict | None:
    """
    Look up the loaded EfficientNet model from sys.modules["app"]
    and run a prediction on the provided PIL image.
    """
    import sys
    app_module = sys.modules.get("app")
    if not app_module:
        logger.debug("app module not found in sys.modules (not fully loaded yet)")
        return None
    
    model = getattr(app_module, "_model", None)
    class_names = getattr(app_module, "_class_names", None)
    device = getattr(app_module, "_device", None)
    
    if model is None or class_names is None or device is None:
        logger.debug("CNN model, class_names, or device not loaded in app module yet")
        return None
        
    try:
        from inference import predict_from_pil
        result = predict_from_pil(pil_image, model, class_names, device)
        return result
    except Exception as e:
        logger.error("Error executing CNN prediction in farming_agent: %s", e)
        return None


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


import httpx
import urllib.parse
from typing import Tuple

# Helper to detect weather‑related queries
def _is_weather_query(query: str) -> bool:
    lowered = query.lower()
    keywords = [
        "weather",
        "temperature",
        "forecast",
        "rain",
        "humidity",
        "sunny",
        "climate",
    ]
    return any(k in lowered for k in keywords)

# Fetch live weather using Open‑Meteo (same logic as irrigation router)
async def _fetch_weather(location: str) -> Tuple[float, float, str]:
    # Returns (temp_celsius, precipitation_probability, matched_name)
    clean_name = location.split(",")[0].strip()
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_name)}&count=1&language=en&format=json"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, timeout=10.0)
        data = res.json()
        if not data.get("results"):
            # fallback to default coordinates (Kolar)
            lat, lon = 13.13768, 78.12999
            matched = location
        else:
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
            matched = f"{data['results'][0]['name']}, {data['results'][0].get('admin1', data['results'][0].get('country'))}"
    # Get current day's forecast (temp max/min and precipitation probability)
    forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
    async with httpx.AsyncClient() as client:
        f_res = await client.get(forecast_url, timeout=10.0)
        f_data = f_res.json()
        daily = f_data.get("daily", {})
        if daily:
            t_max = daily.get("temperature_2m_max", [None])[0]
            t_min = daily.get("temperature_2m_min", [None])[0]
            rain_prob = daily.get("precipitation_probability_max", [0])[0]
            # average temperature for simplicity
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
    "soil", "fertilizer", "fertilizers", "manure", "compost", "vermicompost", "fym", "nitrogen", "phosphorus", "potassium", "potash", "urea", "npk",
    "paddy", "rice", "wheat", "maize", "corn", "cotton", "groundnut", "groundnuts", "peanut", "peanuts", "chilli", "chillies", "chili", "chilis", "tomato", "tomatoes", "onion", "onions", "potato", "potatoes", "brinjal", "eggplant", "cabbage", "cauliflower", "banana", "soybean", "soybeans", "pulse", "pulses", "gram", "chana", "tur", "arhar", "moong", "urad", "mustard", "rapeseed", "sesame", "sesamum", "sunflower", "safflower", "barley", "ragi", "jowar", "sorghum", "bajra", "millet", "millets",
    "seed", "seeds", "seedling", "seedlings", "nursery",
    "irrigation", "irrigate", "water", "watering", "drip", "sprinkler", "monsoon", "rain", "rainfall", "weather", "temperature", "forecast", "climate",
    "pest", "pests", "insect", "insects", "bug", "bugs", "worm", "worms", "bollworm", "hopper", "aphid", "aphids", "thrips", "mite", "mites", "whitefly", "whiteflies", "caterpillar", "caterpillars",
    "disease", "diseases", "fungus", "fungal", "virus", "viral", "bacteria", "bacterial", "blight", "blast", "rot", "mold", "mould", "rust", "mosaic", "wilt", "mildew", "spot", "spots", "canker",
    "pesticide", "pesticides", "insecticide", "insecticides", "fungicide", "fungicides", "herbicide", "herbicides", "weedicide", "weedicides", "weed", "weeds", "weeding",
    "price", "prices", "cost", "costs", "msp", "market", "markets", "mandi", "mandis", "enam", "wholesale", "rate", "rates", "quintal", "rupee", "rupees", "rs", "₹",
    "subsidy", "subsidies", "scheme", "schemes", "loan", "loans", "kisan", "krishi", "rythu", "bandhu", "bima", "credit", "kcc", "pmksy", "pmfby", "pmkisan", "fci", "markfed", "rbk", "enam",
    "yield", "production", "variety", "varieties", "hybrid", "hybrids", "bt", "bpt", "mtu", "nlr", "rnr", "samba", "mahsuri", "teja"
}

def _is_greeting(text: str) -> bool:
    """Check if the text is a simple greeting."""
    import re
    lowered = text.lower().strip()
    cleaned = re.sub(r'[^\w\s]', '', lowered)
    if cleaned in _GREETING_KEYWORDS:
        return True
    words = cleaned.split()
    if len(words) <= 2 and any(w in _GREETING_KEYWORDS for w in words):
        return True
    return False

def _is_agriculture_query(text: str) -> bool:
    """Check if the query text (in English) contains agriculture-related terms."""
    import re
    lowered = text.lower()
    
    # Normalize punctuation/spaces
    tokens = set(re.findall(r'\b\w+\b', lowered))
    
    # Check for direct word matches first
    if tokens.intersection(_AGRI_KEYWORDS):
        return True
        
    # Also check for certain substring matches (e.g. "agri", "krishi", "rythu", "weather")
    substring_keywords = ["agri", "krishi", "rythu", "kisan", "mandi", "weather", "temp", "rain", "irrigate", "fertiliz"]
    for kw in substring_keywords:
        if kw in lowered:
            return True
            
    return False


async def process_query(
    user_message: str,
    image_bytes: bytes | None = None,
    file_bytes: bytes | None = None,
    file_name: str | None = None,
    override_lang: str = "",
) -> AgentResponse:
    """
    Full pipeline: detect language → translate → RAG/CNN/Doc extract → Gemini → translate back.
    """
    # ── 1. Detect language ────────────────────────────────────────────────────
    lang_code, lang_name = detect_language(user_message)
    logger.info("Detected language: %s (%s)", lang_name, lang_code)

    # ── 2. Translate to English for RAG ───────────────────────────────────────
    if lang_code != "en":
        english_query = to_english(user_message, lang_code)
        logger.debug("Translated query: %s", english_query)
    else:
        english_query = user_message

    # Resolve target output language
    if lang_code in ("te", "hi"):
        output_lang = lang_code
    elif override_lang in ("te", "hi"):
        output_lang = override_lang
    else:
        output_lang = lang_code

    # ── 2b. Agriculture Guard ─────────────────────────────────────────────────
    # If the user uploads an image/file or greets the bot, bypass the guard.
    if not (image_bytes or file_bytes) and not _is_greeting(english_query) and not _is_agriculture_query(english_query):
        reject_msg_en = "I am KrishiMitra, your AI agricultural advisor. I can only assist with agriculture, farming, and crop-related queries."
        if output_lang != "en":
            reject_msg_translated = from_english(reject_msg_en, output_lang)
        else:
            reject_msg_translated = reject_msg_en
        logger.info("Query rejected by agriculture guard. Resolved lang: %s", output_lang)
        return AgentResponse(
            response=reject_msg_translated,
            detected_language=lang_code,
            language_name=lang_name,
            agent_type="general",
            sources=[],
            english_query=english_query,
            english_response=reject_msg_en,
        )

    # ── 3. Handle document/text parsing ───────────────────────────────────────
    extracted_text = ""
    if file_bytes and file_name:
        if file_name.lower().endswith(".pdf"):
            extracted_text = _extract_text_from_pdf(file_bytes)
        elif file_name.lower().endswith(".txt"):
            extracted_text = _extract_text_from_txt(file_bytes)
        if extracted_text:
            logger.info("Extracted %d characters from document %s", len(extracted_text), file_name)

    # ── 4. Handle image parsing & local CNN prediction ───────────────────────
    pil_image = None
    cnn_info = ""
    cnn_agent_type = None
    cnn_sources = []

    if image_bytes:
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            cnn_result = _get_cnn_prediction(pil_image)
            if cnn_result:
                predictions_context_parts = []
                for item in cnn_result.get("top_k", []):
                    if item["confidence"] >= 10.0 or item["rank"] == 1:
                        from disease_info import get_disease_info
                        details = get_disease_info(item["class"])
                        p_class = item["class"]
                        p_parts = p_class.split("___")
                        p_plant = p_parts[0].replace("_", " ").strip() if p_parts else "Crop"
                        p_cond = p_parts[1].replace("_", " ").strip() if len(p_parts) > 1 else "Condition"
                        
                        predictions_context_parts.append(
                            f"Prediction Rank {item['rank']}: {p_plant} — {p_cond} (Confidence: {item['confidence']}%)\\n"
                            f"  - Severity: {details.get('severity', 'moderate')}\\n"
                            f"  - Cause: {details.get('cause', 'N/A')}\\n"
                            f"  - Organic Control: {details.get('organic', 'N/A')}\\n"
                            f"  - Chemical Control: {details.get('chemical', 'N/A')}\\n"
                            f"  - Prevention: {details.get('prevention', 'N/A')}"
                        )
                
                if predictions_context_parts:
                    cnn_info = (
                        "CNN DISEASE CLASSIFIER TOP SUGGESTIONS:\\n"
                        + "\\n\\n".join(predictions_context_parts)
                        + "\\n\\nInstructions: Analyze the uploaded image. Check which of the suggestions above fits the visual symptoms (spots, patterns, colors) on the leaf image. Select the most accurate disease and format your response using that suggestion's details (cause, organic/chemical control, prevention). If you are uncertain or the suggestions do not fit, use your general expertise to diagnose but state the alternatives."
                    )
                    cnn_agent_type = "disease"
                    cnn_sources = ["AgriGPT Disease Diagnosis Database 2026"]
                    logger.info("Farming Agent hybrid CNN predictions context compiled. Top rank: %s", cnn_result.get("predicted_class"))
        except Exception as e:
            logger.error("Error during hybrid CNN processing: %s", e)

    # ── 5. Weather detection & RAG retrieval ────────────────────────────────────
    weather_context = ""
    if _is_weather_query(english_query):
        try:
            avg_temp, rain_prob, matched_loc = await _fetch_weather(english_query)
            if avg_temp is not None:
                weather_context = (
                    f"Live Weather for {matched_loc}:\\n"
                    f"- Current average temperature: {avg_temp:.1f}°C\\n"
                    f"- Expected precipitation probability (next day): {rain_prob}%\\n"
                )
        except Exception as e:
            logger.error("Failed to fetch live weather: %s", e)

    chunks = retrieve(english_query)
    context = format_context(chunks)
    if weather_context:
        context = weather_context + "\\n\\n" + context

    agent_type = get_agent_from_chunks(chunks)
    sources = list({c["source"] for c in chunks})

    if cnn_agent_type:
        agent_type = cnn_agent_type
    if cnn_sources:
        sources = list(set(sources + cnn_sources))

    if extracted_text:
        context = f"[Document Content ({file_name})]:\\n{extracted_text}\\n\\n" + context

    # ── 6. Gemini LLM ─────────────────────────────────────────────────────────
    prompt = _build_prompt(english_query, context, cnn_info)
    english_answer = _call_gemini(prompt, pil_image)

    # ── 7. Translate answer back to user's language ───────────────────────────
    if output_lang != "en":
        final_answer = from_english(english_answer, output_lang)
    else:
        final_answer = english_answer

    return AgentResponse(
        response=final_answer,
        detected_language=lang_code,
        language_name=lang_name,
        agent_type=agent_type,
        sources=sources,
        english_query=english_query,
        english_response=english_answer,
    )


