# =============================================================================
# AgriGPT — FastAPI Server  (updated: Feature 3 Fertilizer added)
# Run: python app.py
# =============================================================================

import os
import io
import sys

# Load environment variables from backend/.env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import uvicorn

# ── Resolve paths ─────────────────────────────────────────────────────────────
BASE_DIR     = os.path.join(os.path.dirname(__file__), "saved_models")
WEIGHTS_PATH = os.path.join(BASE_DIR, "agrigpt_production_weights.pth")
CLASSES_PATH = os.path.join(BASE_DIR, "class_names.json")

# ── Feature 1: Disease Detection ──────────────────────────────────────────────
from inference import load_model, predict_from_pil

# ── Feature 3: Fertilizer RAG engine ─────────────────────────────────────────
from fertilizer.rag_engine import load_rag_engine
from fertilizer.router import router as fertilizer_router

# ── Feature 6: Government Schemes Q&A ────────────────────────────────────────
from schemes.rag_engine import load_schemes_engine
from schemes.router import router as schemes_router

# ── Feature 5: Weather-Based Irrigation Planning (Agent 2) ───────────────────
from irrigation.router import router as irrigation_router

# ── Feature 7: Crop Price Prediction & Market Advisor ────────────────────────
from market import load_market_graph
from market import router as market_router

# ── Disease knowledge base (unchanged) ───────────────────────────────────────
DISEASE_INFO = {
    "Tomato___Early_blight": {
        "severity": "moderate",
        "cause": "Fungal infection caused by Alternaria solani. Spreads in warm, humid conditions.",
        "organic": "Spray neem oil solution (5ml/litre) every 7 days. Remove infected leaves immediately.",
        "chemical": "Apply Mancozeb 75% WP @ 2g/litre or Chlorothalonil 75% WP @ 2g/litre. Spray every 10 days.",
        "prevention": "Maintain proper plant spacing for air circulation. Avoid overhead watering.",
    },
    "Tomato___Late_blight": {
        "severity": "severe",
        "cause": "Oomycete Phytophthora infestans. Spreads rapidly in cool, wet weather.",
        "organic": "Spray copper-based fungicide (Bordeaux mixture 1%) every 5–7 days.",
        "chemical": "Apply Metalaxyl + Mancozeb (Ridomil Gold) @ 2.5g/litre.",
        "prevention": "Plant resistant varieties (Arka Rakshak). Avoid planting tomato near potato.",
    },
    "Tomato___Leaf_Mold": {
        "severity": "mild",
        "cause": "Passalora fulva fungus. Yellow patches on upper leaf, olive-green mold on underside.",
        "organic": "Improve ventilation. Spray potassium bicarbonate solution.",
        "chemical": "Apply Chlorothalonil 75% WP @ 2g/litre every 10 days.",
        "prevention": "Reduce humidity in greenhouse. Space plants well.",
    },
    "Tomato___Bacterial_spot": {
        "severity": "moderate",
        "cause": "Xanthomonas bacteria. Small dark water-soaked spots on leaves and fruit.",
        "organic": "Spray copper-based bactericide (Bordeaux mixture). Remove infected debris.",
        "chemical": "Apply Copper Oxychloride 50% WP @ 3g/litre.",
        "prevention": "Use disease-free certified seeds. Disinfect tools.",
    },
    "Tomato___Septoria_leaf_spot": {
        "severity": "moderate",
        "cause": "Septoria lycopersici fungus. Small circular spots with dark borders and light centers.",
        "organic": "Remove lower infected leaves. Apply compost tea spray.",
        "chemical": "Apply Mancozeb 75% WP @ 2g/litre every 10 days.",
        "prevention": "Rotate crops. Avoid splashing water on leaves.",
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "severity": "moderate",
        "cause": "Tetranychus urticae mites. Tiny yellow stippling on leaves, webbing underneath.",
        "organic": "Spray strong jets of water to dislodge mites. Apply neem oil or insecticidal soap.",
        "chemical": "Apply Abamectin 1.8% EC @ 0.5ml/litre.",
        "prevention": "Maintain adequate soil moisture. Monitor plants regularly.",
    },
    "Tomato___Target_Spot": {
        "severity": "moderate",
        "cause": "Corynespora cassiicola fungus. Concentric ring (target) pattern on brown leaf spots.",
        "organic": "Remove infected leaves. Spray copper-based fungicide.",
        "chemical": "Apply Azoxystrobin 23% SC @ 1ml/litre.",
        "prevention": "Avoid dense planting. Stake plants.",
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "severity": "severe",
        "cause": "TYLCV transmitted by whiteflies.",
        "organic": "Use reflective mulch to deter whiteflies. Install yellow sticky traps.",
        "chemical": "Control whiteflies with Imidacloprid 17.8% SL @ 0.5ml/litre.",
        "prevention": "Use TYLCV-resistant varieties. Rogue out infected plants early.",
    },
    "Tomato___Tomato_mosaic_virus": {
        "severity": "severe",
        "cause": "Tomato Mosaic Virus (ToMV). Mosaic pattern, distorted leaves.",
        "organic": "Remove and destroy infected plants. Disinfect hands and tools with soap.",
        "chemical": "No direct cure. Control aphid vectors with Dimethoate 30% EC @ 2ml/litre.",
        "prevention": "Use virus-indexed seeds. Wash hands before handling plants.",
    },
    "Tomato___healthy": {
        "severity": "none",
        "cause": "No disease detected. Leaf appears healthy.",
        "organic": "Continue regular monitoring. Maintain balanced fertilization with NPK.",
        "chemical": "No treatment required.",
        "prevention": "Maintain proper irrigation and plant hygiene.",
    },
    "Potato___Early_blight": {
        "severity": "moderate",
        "cause": "Alternaria solani fungus. Target-shaped brown spots on older leaves first.",
        "organic": "Apply Bacillus subtilis biofungicide. Spray compost tea every 10 days.",
        "chemical": "Apply Mancozeb 75% WP @ 2g/litre.",
        "prevention": "Ensure balanced fertilization. Destroy crop debris after harvest.",
    },
    "Potato___Late_blight": {
        "severity": "severe",
        "cause": "Phytophthora infestans. Dark water-soaked lesions.",
        "organic": "Spray Bordeaux mixture (1%) as preventive. Remove and bury infected plants.",
        "chemical": "Apply Metalaxyl 8% + Mancozeb 64% WP @ 2.5g/litre at first symptom.",
        "prevention": "Use certified disease-free seed tubers. Plant resistant varieties.",
    },
    "Potato___healthy": {
        "severity": "none",
        "cause": "No disease detected. Leaf appears healthy.",
        "organic": "Continue regular monitoring.",
        "chemical": "No treatment required.",
        "prevention": "Maintain proper irrigation and hygiene.",
    },
    "Pepper,_bell___Bacterial_spot": {
        "severity": "moderate",
        "cause": "Xanthomonas bacteria. Dark water-soaked spots on leaves.",
        "organic": "Spray copper-based bactericide. Remove infected leaves.",
        "chemical": "Apply Copper Oxychloride 50% WP @ 3g/litre.",
        "prevention": "Use disease-free seeds. Practice crop rotation.",
    },
    "Pepper,_bell___healthy": {
        "severity": "none",
        "cause": "No disease detected. Leaf appears healthy.",
        "organic": "Continue regular monitoring.",
        "chemical": "No treatment required.",
        "prevention": "Maintain proper plant spacing.",
    },
}

CONFIDENCE_THRESHOLD = 0.25


def get_disease_info(class_name: str) -> dict:
    if class_name in DISEASE_INFO:
        return DISEASE_INFO[class_name]
    parts    = class_name.split("___")
    plant    = parts[0].replace("_", " ").strip() if parts else "Crop"
    disease  = parts[1].replace("_", " ").strip() if len(parts) > 1 else "Condition"
    severity = "none" if "healthy" in class_name.lower() else "moderate"
    return {
        "severity": severity,
        "cause": f"Detected: {disease} affecting {plant} leaves.",
        "organic": "Apply organic neem oil formulation (5ml/Litre) every 7 days.",
        "chemical": "Consult your nearest agricultural extension branch.",
        "prevention": "Sanitize tools, ensure healthy airflow, regulate irrigation.",
    }


# =============================================================================
# APP SETUP
# =============================================================================
app = FastAPI(title="AgriGPT API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Feature 3 router ──────────────────────────────────────────────────
app.include_router(fertilizer_router)

# ── Include Feature 6 router ──────────────────────────────────────────────────
app.include_router(schemes_router)

# ── Include Feature 5 router ──────────────────────────────────────────────────
app.include_router(irrigation_router)

# ── Include Feature 7 router ──────────────────────────────────────────────────
app.include_router(market_router)


# =============================================================================
# STARTUP — load models
# =============================================================================
@app.on_event("startup")
async def startup_event():
    global _model, _class_names, _device

    # Feature 1: Disease detection model
    print("[AgriGPT] Loading disease detection model…")
    _model, _class_names, _device = load_model(
        weights_path=WEIGHTS_PATH,
        classes_path=CLASSES_PATH,
    )
    print(f"[AgriGPT] Disease model ready — {len(_class_names)} classes on [{_device}]")

    # Feature 3: Fertilizer RAG engine
    print("[AgriGPT] Loading fertilizer RAG engine…")
    try:
        load_rag_engine()
        print("[AgriGPT] Fertilizer RAG engine ready.")
    except EnvironmentError as e:
        print(f"[AgriGPT] [WARNING] Fertilizer RAG skipped: {e}")

    # Feature 6: Government Schemes Q&A
    print("[AgriGPT] Loading government schemes RAG engine…")
    try:
        load_schemes_engine()
        print("[AgriGPT] Government schemes RAG engine ready.")
    except EnvironmentError as e:
        print(f"[AgriGPT] [WARNING] Government schemes RAG skipped: {e}")

    # Feature 7: Market Advisor Graph
    print("[AgriGPT] Loading market advisor graph…")
    try:
        load_market_graph()
        print("[AgriGPT] Market advisor graph ready.")
    except Exception as e:
        print(f"[AgriGPT] [WARNING] Market advisor graph skipped: {e}")


_model       = None
_class_names = None
_device      = None


# =============================================================================
# FEATURE 1 — DISEASE DETECTION
# =============================================================================
@app.get("/health")
def health():
    return {
        "status"  : "ok",
        "classes" : len(_class_names) if _class_names else 0,
        "device"  : _device,
    }


@app.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPG or PNG)")

    contents  = await file.read()
    pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    result    = predict_from_pil(pil_image, _model, _class_names, _device, top_k=5)

    top_confidence = result["confidence"] / 100.0
    top_class      = result["predicted_class"]
    plant_name     = result["plant"]
    condition_name = result["condition"]

    if top_confidence < CONFIDENCE_THRESHOLD:
        return {
            "status"             : "uncertain",
            "message"            : "Could not confidently identify the disease. Please upload a clearer close-up leaf photo.",
            "confidence"         : round(top_confidence * 100, 1),
            "top_predictions"    : [
                {"class": item["class"], "confidence": item["confidence"]}
                for item in result["top_k"]
            ],
            "consult_agronomist" : True,
        }

    info = get_disease_info(top_class)

    return {
        "status"             : "success",
        "plant"              : plant_name,
        "disease"            : condition_name,
        "class_id"           : top_class,
        "confidence"         : round(top_confidence * 100, 1),
        "severity"           : info["severity"],
        "cause"              : info["cause"],
        "organic_treatment"  : info["organic"],
        "chemical_treatment" : info["chemical"],
        "prevention_tips"    : info["prevention"],
        "consult_agronomist" : top_confidence < 0.80,
        "top5"               : [
            {
                "class"      : item["class"].replace("___", " — ").replace("_", " "),
                "confidence" : item["confidence"],
            }
            for item in result["top_k"]
        ],
    }


# =============================================================================
# FEATURE 4 — SOIL HEALTH ANALYSIS (Gemini version)
# =============================================================================
from pydantic import BaseModel

class SoilAnalyseRequest(BaseModel):
    ph: float
    n: float
    p: float
    k: float
    texture: str
    grade: str
    lang: str = "en"


@app.post("/soil/analyse")
async def soil_analyse(req: SoilAnalyseRequest):
    import json
    import asyncio
    from fastapi.responses import StreamingResponse
    import google.generativeai as genai

    lang = req.lang if req.lang in ("en", "te", "hi") else "en"

    lang_map = {
        "en": "Respond entirely in English.",
        "te": "Respond entirely in Telugu (\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41). Use Telugu script for all text content.",
        "hi": "Respond entirely in Hindi (\u0939\u093f\u0928\u094d\u0926\u0940). Use Devanagari script for all text content.",
    }
    lang_instruction = lang_map[lang]

    # Evaluate statuses locally to assist the LLM
    n_status = "deficient (Very Low)" if req.n < 120 else ("low" if req.n < 180 else "good/optimal")
    p_status = "deficient (Very Low)" if req.p < 15 else ("low" if req.p < 30 else "good/optimal")
    k_status = "deficient (Very Low)" if req.k < 100 else ("low" if req.k < 160 else "good/optimal")
    ph_status = "acidic (low)" if req.ph < 6.0 else ("alkaline (high)" if req.ph > 7.5 else "neutral (optimal)")

    prompt = f"""You are AgriGPT's soil health expert for Indian farmers (Telangana/Andhra Pradesh focus).

{lang_instruction}

Soil test values and their evaluated statuses:
- pH: {req.ph} (Status: {ph_status})
- Nitrogen (N): {req.n} kg/ha (Status: {n_status})
- Phosphorus (P): {req.p} kg/ha (Status: {p_status})
- Potassium (K): {req.k} kg/ha (Status: {k_status})
- Soil texture: {req.texture} (Note: 'loamy' texture is translated as '\u0c26\u0c41\u0c02\u0c2a \u0c28\u0c47\u0c32' in Telugu, meaning root/tuber crop soil)
- Overall soil grade: {req.grade}

Provide a structured response with EXACTLY these three sections. Keep the section headers in English:

TOP 3 CROPS:
List exactly 3 crops best suited for these soil conditions with suitability % (e.g. "Tomato — 92%").
* If the soil texture is 'loamy' ('\u0c26\u0c41\u0c02\u0c2a \u0c28\u0c47\u0c32'), prioritize root/tuber crops (such as Ginger, Turmeric, Sweet Potato, Cassava) or loamy-loving vegetables.

DEFICIENCIES:
List the evaluated status of each parameter (including pH and NPK).
* Explicitly state if pH is optimal or if there's an issue (acidic/alkaline) and what it means for nutrient uptake.
* For N, P, and K, comment ONLY on the ones that are low or deficient. If a nutrient status is good/optimal, state that it is sufficient. Do NOT confuse low/deficient nutrients.

IMPROVEMENT PLAN:
Give exactly 3 numbered actionable soil improvement tips customized to the deficiencies identified:
* Tip 1: Organic matter / carbon building.
* Tip 2: Correcting the specific nutrient deficiencies (e.g., if Potassium is low/deficient, recommend MOP or potassium-rich fertilizers; if Phosphorus is low/deficient, recommend SSP/DAP; if Nitrogen is low/deficient, recommend Urea).
* Tip 3: pH correction — IMPORTANT: if pH is acidic (<6.0), recommend agricultural lime; if pH is alkaline (>7.5), recommend Elemental Sulfur (NOT gypsum — gypsum does not lower pH; sulfur converts to sulfuric acid in soil and actively lowers pH); if pH is optimal, give a general micro-nutrient/organic tip.

IMPORTANT: The section headers (TOP 3 CROPS, DEFICIENCIES, IMPROVEMENT PLAN) MUST stay in English. All other content must be in the language specified above.
Be concise, practical, and farmer-friendly. No markdown bold, no extra headers."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured. Set it in backend/.env")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    async def generate():
        use_fallback = False
        try:
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    data = {
                        "type": "content_block_delta",
                        "delta": {"text": chunk.text}
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"[Soil Analyse] Gemini API call failed or key is invalid ({e}). Falling back to simulated streaming analysis.")
            use_fallback = True
            
        if use_fallback:
            # Evaluated statuses
            n_s = "deficient" if req.n < 120 else ("low" if req.n < 180 else "optimal")
            p_s = "deficient" if req.p < 15 else ("low" if req.p < 30 else "optimal")
            k_s = "deficient" if req.k < 100 else ("low" if req.k < 160 else "optimal")
            ph_s = "acidic" if req.ph < 6.0 else ("alkaline" if req.ph > 7.5 else "optimal")

            # Localized crops (prioritizing root/tuber crops for loamy soil)
            _crops = {
                "en": {
                    "black": [("Cotton", 94), ("Paddy", 88), ("Chilli", 85)],
                    "clay": [("Paddy", 91), ("Maize", 83), ("Sorghum", 78)],
                    "sandy": [("Groundnut", 92), ("Chilli", 84), ("Sesame", 79)],
                    "loamy": [("Sweet Potato", 92), ("Ginger", 88), ("Tomato", 85)]
                },
                "te": {
                    "black": [("\u0c2a\u0c24\u0c4d\u0c24\u0c3f (Cotton)", 94), ("\u0c35\u0c30\u0c3f (Paddy)", 88), ("\u0c2e\u0c3f\u0c30\u0c2a (Chilli)", 85)],
                    "clay": [("\u0c35\u0c30\u0c3f (Paddy)", 91), ("\u0c2e\u0c4a\u0c15\u0c4d\u0c15\u0c1c\u0c4a\u0c28\u0c4d\u0c28 (Maize)", 83), ("\u0c1c\u0c4a\u0c28\u0c4d\u0c28 (Sorghum)", 78)],
                    "sandy": [("\u0c35\u0c47\u0c30\u0c41\u0c36\u0c46\u0c28\u0c17 (Groundnut)", 92), ("\u0c2e\u0c3f\u0c30\u0c2a (Chilli)", 84), ("\u0c28\u0c41\u0c35\u0c4d\u0c35\u0c41\u0c32\u0c41 (Sesame)", 79)],
                    "loamy": [("\u0c1a\u0c3f\u0c32\u0c17\u0c21\u0c26\u0c41\u0c02\u0c2a (Sweet Potato)", 92), ("\u0c05\u0c32\u0c4d\u0c32\u0c02 (Ginger)", 88), ("\u0c1f\u0c2e\u0c4b\u0c1f\u0c3e (Tomato)", 85)]
                },
                "hi": {
                    "black": [("\u0915\u092a\u093e\u0938 (Cotton)", 94), ("\u0927\u093e\u0928 (Paddy)", 88), ("\u092e\u093f\u0930\u094d\u091a (Chilli)", 85)],
                    "clay": [("\u0927\u093e\u0928 (Paddy)", 91), ("\u092e\u0915\u094d\u0915\u093e (Maize)", 83), ("\u091c\u094d\u0935\u093e\u0930 (Sorghum)", 78)],
                    "sandy": [("\u092e\u0942\u0902\u0917\u092b\u0932\u0940 (Groundnut)", 92), ("\u092e\u093f\u0930\u094d\u091a (Chilli)", 84), ("\u0924\u093f\u0932 (Sesame)", 79)],
                    "loamy": [("\u0936\u0915\u0930\u0915\u0902\u0926 (Sweet Potato)", 92), ("\u0905\u0926\u0930\u0915 (Ginger)", 88), ("\u091f\u092e\u093e\u091f\u0930 (Tomato)", 85)]
                },
            }

            _ph_desc = {
                "en": {
                    "acidic": f"Soil pH is acidic ({req.ph}). This limits availability of key nutrients.",
                    "alkaline": f"Soil pH is alkaline ({req.ph}). This can lock micronutrients like zinc and iron.",
                    "optimal": f"Soil pH is optimal ({req.ph}), which is excellent for nutrient absorption."
                },
                "te": {
                    "acidic": f"\u0c28\u0c47\u0c32 pH \u0c06\u0c2e\u0c4d\u0c32\u0c24\u0c4d\u0c35\u0c02\u0c17\u0c3e \u0c09\u0c02\u0c26\u0c3f ({req.ph}). \u0c07\u0c26\u0c3f \u0c2e\u0c41\u0c16\u0c4d\u0c2f\u0c2e\u0c48\u0c28 \u0c2a\u0c4b\u0c37\u0c15\u0c3e\u0c32 \u0c32\u0c2d\u0c4d\u0c2f\u0c24\u0c28\u0c41 \u0c2a\u0c30\u0c3f\u0c2e\u0c3f\u0c24\u0c02 \u0c1a\u0c47\u0c38\u0c4d\u0c24\u0c41\u0c02\u0c26\u0c3f.",
                    "alkaline": f"\u0c28\u0c47\u0c32 pH \u0c15\u0c4d\u0c37\u0c3e\u0c30\u0c24\u0c4d\u0c35\u0c02\u0c17\u0c3e \u0c09\u0c02\u0c26\u0c3f ({req.ph}). \u0c07\u0c26\u0c3f \u0c1c\u0c3f\u0c02\u0c15\u0c4d \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c07\u0c28\u0c41\u0c2e\u0c41 \u0c35\u0c02\u0c1f\u0c3f \u0c38\u0c42\u0c15\u0c4d\u0c37\u0c4d\u0c2e\u0c2a\u0c4b\u0c37\u0c15\u0c3e\u0c32\u0c28\u0c41 \u0c28\u0c3f\u0c30\u0c4b\u0c27\u0c3f\u0c38\u0c4d\u0c24\u0c41\u0c02\u0c26\u0c3f.",
                    "optimal": f"\u0c28\u0c47\u0c32 pH \u0c24\u0c1f\u0c38\u0c4d\u0c25\u0c02\u0c17\u0c3e/\u0c38\u0c30\u0c48\u0c28\u0c26\u0c3f\u0c17\u0c3e \u0c09\u0c02\u0c26\u0c3f ({req.ph}), \u0c07\u0c26\u0c3f \u0c2a\u0c4b\u0c37\u0c15\u0c3e\u0c32 \u0c36\u0c4b\u0c37\u0c23\u0c15\u0c41 \u0c1a\u0c3e\u0c32\u0c3e \u0c2e\u0c02\u0c1a\u0c3f\u0c26\u0c3f."
                },
                "hi": {
                    "acidic": f"\u092e\u093f\u091f\u094d\u091f\u0940 \u0915\u093e pH \u0905\u092e\u094d\u0932\u0940\u092f \u0939\u0948 ({req.ph}). \u092f\u0939 \u092e\u0941\u0916\u094d\u092f \u092a\u094b\u0937\u0915 \u0924\u0924\u094d\u0935\u094b\u0902 \u0915\u0940 \u0909\u092a\u0932\u092c\u094d\u0927\u0924\u093e \u0915\u094b \u0938\u0940\u092e\u093f\u0924 \u0915\u0930\u0924\u093e \u0939\u0948.",
                    "alkaline": f"\u092e\u093f\u091f\u094d\u091f\u0940 \u0915\u093e pH \u0915\u094d\u0937\u093e\u0930\u0940\u092f \u0939\u0948 ({req.ph}). \u092f\u0939 \u091c\u093f\u0902\u0915 \u0914\u0930 \u0932\u094b\u0939\u0947 \u091c\u0948\u0938\u0947 \u0938\u0942\u0915\u094d\u0937\u094d\u092e \u092a\u094b\u0937\u0915 \u0924\u0924\u094d\u0935\u094b\u0902 \u0915\u094b \u0905\u0935\u0930\u094b\u0927\u093f\u0924 \u0915\u0930\u0924\u093e \u0939\u0948.",
                    "optimal": f"\u092e\u093f\u091f\u094d\u091f\u0940 \u0915\u093e pH \u0905\u0928\u0941\u0915\u0942\u0932 \u0939\u0948 ({req.ph}), \u091c\u094b \u092a\u094b\u0937\u0915 \u0924\u0924\u094d\u0935\u094b\u0902 \u0915\u0947 \u0905\u0935\u0936\u094b\u0937\u0923 \u0915\u0947 \u0932\u093f\u090f \u0909\u0924\u094d\u0915\u0943\u0937\u094d\u091f \u0939\u0948."
                }
            }

            _sl = {"en": {"deficient": "deficient", "low": "low"}, "te": {"deficient": "\u0c32\u0c4b\u0c2a\u0c02", "low": "\u0c24\u0c15\u0c4d\u0c15\u0c41\u0c35"}, "hi": {"deficient": "\u0915\u092e\u0940", "low": "\u0915\u092e"}}
            
            _def_t = {
                "en": {
                    "N": "Nitrogen (N) is {s} ({v} kg/ha). Causes yellowing of older leaves and stunted growth.",
                    "P": "Phosphorus (P) is {s} ({v} kg/ha). Limits root development and delays crop maturity.",
                    "K": "Potassium (K) is {s} ({v} kg/ha). Reduces disease resistance and fruit quality.",
                },
                "te": {
                    "N": "\u0c28\u0c24\u0c4d\u0c30\u0c1c\u0c28\u0c3f (N) {s} ({v} \u0c15\u0c3f.\u0c17\u0c4d\u0c30\u0c3e/\u0c39\u0c46). \u0c2a\u0c3e\u0c24 \u0c06\u0c15\u0c41\u0c32 \u0c2a\u0c38\u0c41\u0c2a\u0c41 \u0c30\u0c02\u0c17\u0c41 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c2e\u0c02\u0c26\u0c17\u0c3f\u0c02\u0c1a\u0c3f\u0c28 \u0c2a\u0c46\u0c30\u0c41\u0c17\u0c41\u0c26\u0c32\u0c15\u0c41 \u0c15\u0c3e\u0c30\u0c23\u0c02.",
                    "P": "\u0c2d\u0c3e\u0c38\u0c4d\u0c35\u0c30\u0c02 (P) {s} ({v} \u0c15\u0c3f.\u0c17\u0c4d\u0c30\u0c3e/\u0c39\u0c46). \u0c35\u0c47\u0c30\u0c41 \u0c05\u0c2d\u0c3f\u0c35\u0c43\u0c26\u0c4d\u0c27\u0c3f\u0c28\u0c3f \u0c2a\u0c30\u0c3f\u0c2e\u0c3f\u0c24\u0c02 \u0c1a\u0c47\u0c38\u0c4d\u0c24\u0c41\u0c02\u0c26\u0c3f \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c2a\u0c02\u0c1f \u0c2a\u0c30\u0c3f\u0c2a\u0c15\u0c4d\u0c35\u0c24\u0c28\u0c41 \u0c06\u0c32\u0c38\u0c4d\u0c2f\u0c02 \u0c1a\u0c47\u0c38\u0c4d\u0c24\u0c41\u0c02\u0c26\u0c3f.",
                    "K": "\u0c2a\u0c4a\u0c1f\u0c3e\u0c37\u0c3f\u0c2f\u0c02 (K) {s} ({v} \u0c15\u0c3f.\u0c17\u0c4d\u0c30\u0c3e/\u0c39\u0c46). \u0c35\u0c4d\u0c2f\u0c3e\u0c27\u0c3f \u0c28\u0c3f\u0c30\u0c4b\u0c27\u0c15\u0c24 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c2a\u0c02\u0c21\u0c41 \u0c28\u0c3e\u0c23\u0c4d\u0c2f\u0c24\u0c28\u0c41 \u0c24\u0c17\u0c4d\u0c17\u0c3f\u0c38\u0c4d\u0c24\u0c41\u0c02\u0c26\u0c3f.",
                },
                "hi": {
                    "N": "\u0928\u093e\u0907\u091f\u094d\u0930\u094b\u091c\u0928 (N) {s} ({v} \u0915\u093f\u0917\u094d\u0930\u093e/\u0939\u0947). \u092a\u0941\u0930\u093e\u0928\u0940 \u092a\u0924\u094d\u0924\u093f\u092f\u094b\u0902 \u0915\u093e \u092a\u0940\u0932\u093e\u092a\u0928 \u0914\u0930 \u0905\u0935\u0930\u0941\u0926\u094d\u0927 \u0935\u0943\u0926\u094d\u0927\u093f \u0915\u093e \u0915\u093e\u0930\u0923.",
                    "P": "\u092b\u093e\u0938\u094d\u092b\u094b\u0930\u0938 (P) {s} ({v} \u0915\u093f\u0917\u094d\u0930\u093e/\u0939\u0947). \u091c\u0921\u093c \u0935\u093f\u0915\u093e\u0938 \u0915\u094b \u0938\u0940\u092e\u093f\u0924 \u0915\u0930\u0924\u093e \u0939\u0948 \u0914\u0930 \u092b\u0938\u0932 \u092a\u0930\u093f\u092a\u0915\u094d\u0935\u0924\u093e \u092e\u0947\u0902 \u0926\u0947\u0930\u0940 \u0915\u0930\u0924\u093e \u0939\u0948.",
                    "K": "\u092a\u094b\u091f\u0948\u0936\u093f\u092f\u092e (K) {s} ({v} \u0915\u093f\u0917\u094d\u0930\u093e/\u0939\u0947). \u0930\u094b\u0917 \u092a\u094d\u0930\u0924\u093f\u0930\u094b\u0927\u0915 \u0915\u094d\u0937\u092e\u0924\u093e \u0914\u0930 \u092b\u0932 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0915\u092e \u0915\u0930\u0924\u093e \u0939\u0948.",
                },
            }

            _tips = {
                "en": {
                    "organic": "Add 5-10 tonnes/ha of well-decomposed FYM or compost to build organic carbon.",
                    "N": "Apply Urea in split doses to correct Nitrogen deficiency.",
                    "P": "Apply SSP (Single Super Phosphate) or DAP to correct Phosphorus deficiency.",
                    "K": "Apply MOP (Muriate of Potash) to correct Potassium deficiency.",
                    "lime": "Apply agricultural lime to neutralize soil acidity.",
                    "gypsum": "Apply Elemental Sulfur (not gypsum) to reduce alkaline pH. Sulfur converts to sulfuric acid in the soil via microbes, actively lowering the pH level.",
                    "general": "Maintain regular crop rotation and green manuring (dhaincha) to preserve fertility."
                },
                "te": {
                    "organic": "\u0c38\u0c47\u0c02\u0c26\u0c4d\u0c30\u0c3f\u0c2f \u0c15\u0c3e\u0c30\u0c4d\u0c2c\u0c28\u0c4d \u0c2a\u0c46\u0c02\u0c1a\u0c21\u0c3e\u0c28\u0c3f\u0c15\u0c3f 5-10 \u0c1f\u0c28\u0c4d\u0c28\u0c41\u0c32\u0c41/\u0c39\u0c46\u0c15\u0c4d\u0c1f\u0c3e\u0c30\u0c41\u0c15\u0c41 \u0c2c\u0c3e\u0c17\u0c3e \u0c15\u0c41\u0c33\u0c4d\u0c33\u0c3f\u0c28 \u0c2a\u0c36\u0c41\u0c35\u0c41\u0c32 \u0c0e\u0c30\u0c41\u0c35\u0c41 \u0c32\u0c47\u0c26\u0c3e \u0c15\u0c02\u0c2a\u0c4b\u0c38\u0c4d\u0c1f\u0c4d \u0c15\u0c32\u0c2a\u0c02\u0c21\u0c3f.",
                    "N": "\u0c28\u0c24\u0c4d\u0c30\u0c1c\u0c28\u0c3f \u0c32\u0c4b\u0c2a\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c38\u0c30\u0c3f\u0c26\u0c3f\u0c26\u0c4d\u0c26\u0c21\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c2f\u0c42\u0c30\u0c3f\u0c2f\u0c3e\u0c28\u0c41 \u0c35\u0c3f\u0c2d\u0c1c\u0c3f\u0c24 \u0c2e\u0c4b\u0c24\u0c3e\u0c26\u0c41\u0c32\u0c4d\u0c32\u0c4b \u0c35\u0c47\u0c2f\u0c02\u0c21\u0c3f.",
                    "P": "\u0c2d\u0c3e\u0c38\u0c4d\u0c35\u0c30\u0c02 \u0c32\u0c4b\u0c2a\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c38\u0c30\u0c3f\u0c26\u0c3f\u0c26\u0c4d\u0c26\u0c21\u0c3e\u0c28\u0c3f\u0c15\u0c3f SSP \u0c32\u0c47\u0c26\u0c3e DAP \u0c35\u0c47\u0c2f\u0c02\u0c21\u0c3f.",
                    "K": "\u0c2a\u0c4a\u0c1f\u0c3e\u0c37\u0c3f\u0c2f\u0c02 \u0c32\u0c4b\u0c2a\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c38\u0c30\u0c3f\u0c26\u0c3f\u0c26\u0c4d\u0c26\u0c21\u0c3e\u0c28\u0c3f\u0c15\u0c3f MOP (\u0c2e\u0c4d\u0c2f\u0c42\u0c30\u0c3f\u0c2f\u0c47\u0c1f\u0c4d \u0c06\u0c2b\u0c4d \u0c2a\u0c4a\u0c1f\u0c3e\u0c37\u0c4d) \u0c35\u0c47\u0c2f\u0c02\u0c21\u0c3f.",
                    "lime": "\u0c28\u0c47\u0c32 \u0c06\u0c2e\u0c4d\u0c32\u0c24\u0c4d\u0c35\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c24\u0c17\u0c4d\u0c17\u0c3f\u0c02\u0c1a\u0c21\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c35\u0c4d\u0c2f\u0c35\u0c38\u0c3e\u0c2f \u0c38\u0c41\u0c28\u0c4d\u0c28\u0c02 \u0c35\u0c47\u0c2f\u0c02\u0c21\u0c3f.",
                    "gypsum": "\u0c28\u0c47\u0c32 \u0c15\u0c4d\u0c37\u0c3e\u0c30\u0c24\u0c4d\u0c35\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c24\u0c17\u0c4d\u0c17\u0c3f\u0c02\u0c1a\u0c21\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c2e\u0c42\u0c32\u0c15 \u0c17\u0c02\u0c27\u0c15\u0c02 (Elemental Sulfur) \u0c35\u0c47\u0c2f\u0c02\u0c21\u0c3f. \u0c17\u0c02\u0c27\u0c15\u0c02 \u0c28\u0c47\u0c32\u0c32\u0c4b \u0c38\u0c32\u0c4d\u0c2b\u0c4d\u0c2f\u0c42\u0c30\u0c3f\u0c15\u0c4d \u0c06\u0c2e\u0c4d\u0c32\u0c02\u0c17\u0c3e \u0c2e\u0c3e\u0c30\u0c3f pH \u0c28\u0c3f \u0c24\u0c17\u0c4d\u0c17\u0c3f\u0c38\u0c4d\u0c24\u0c41\u0c02\u0c26\u0c3f.",
                    "general": "\u0c28\u0c47\u0c32 \u0c38\u0c3e\u0c30\u0c35\u0c02\u0c24\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c15\u0c3e\u0c2a\u0c3e\u0c21\u0c1f\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c15\u0c4d\u0c30\u0c2e\u0c02 \u0c24\u0c2a\u0c4d\u0c2a\u0c15\u0c41\u0c02\u0c21\u0c3e \u0c2a\u0c02\u0c1f \u0c2e\u0c3e\u0c30\u0c4d\u0c2a\u0c3f\u0c21\u0c3f \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c2a\u0c1a\u0c4d\u0c1a\u0c3f\u0c30\u0c4a\u0c1f\u0c4d\u0c1f \u0c0e\u0c30\u0c41\u0c35\u0c41\u0c32 \u0c38\u0c3e\u0c17\u0c41 \u0c1a\u0c47\u0c2f\u0c02\u0c21\u0c3f."
                },
                "hi": {
                    "organic": "\u091c\u0948\u0935\u093f\u0915 \u0915\u093e\u0930\u094d\u092c\u0928 \u092c\u0922\u093c\u093e\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f 5-10 \u091f\u0928/\u0939\u0947\u0915\u094d\u091f\u0947\u092f\u0930 \u0905\u091a\u094d\u091b\u0940 \u0924\u0930\u0939 \u0938\u0947 \u0938\u0921\u093c\u0940 \u0939\u0941\u0908 \u0917\u094b\u092c\u0930 \u0915\u0940 \u0916\u093e\u0926 \u092f\u093e \u0915\u092e\u094d\u092a\u094b\u0938\u094d\u091f \u092e\u093f\u0932\u093e\u090f\u0902.",
                    "N": "\u0928\u093e\u0907\u091f\u094d\u0930\u094b\u091c\u0928 \u0915\u0940 \u0915\u092e\u0940 \u0915\u094b \u0926\u0942\u0930 \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u092f\u0942\u0930\u093f\u092f\u093e \u0915\u094b \u0935\u093f\u092d\u093e\u091c\u093f\u0924 \u0916\u0941\u0930\u093e\u0915 \u092e\u0947\u0902 \u0921\u093e\u0932\u0947\u0902.",
                    "P": "\u092b\u093e\u0938\u094d\u092b\u094b\u0930\u0938 \u0915\u0940 \u0915\u092e\u0940 \u0915\u094b \u0926\u0942\u0930 \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f SSP \u092f\u093e DAP \u0921\u093e\u0932\u0947\u0902.",
                    "K": "\u092a\u094b\u091f\u0947\u0936\u093f\u092f\u092e \u0915\u0940 \u0915\u092e\u0940 \u0915\u094b \u0926\u0942\u0930 \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f MOP (\u092e\u094d\u092f\u0942\u0930\u093f\u090f\u091f \u0911\u092b \u092a\u094b\u091f\u093e\u0936) \u0921\u093e\u0932\u0947\u0902.",
                    "lime": "\u092e\u093f\u091f\u094d\u091f\u0940 \u0915\u0940 \u0905\u092e\u094d\u0932\u0924\u093e \u0915\u094b \u0915\u092e \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u0915\u0943\u0937\u093f \u091a\u0942\u0928\u093e \u0921\u093e\u0932\u0947\u0902.",
                    "gypsum": "\u092e\u093f\u091f\u094d\u091f\u0940 \u0915\u0940 \u0915\u094d\u0937\u093e\u0930\u0940\u092f\u0924\u093e \u0915\u094b \u0915\u092e \u0915\u0930\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u092e\u0942\u0932 \u0917\u0902\u0927\u0915 (Elemental Sulfur) \u0921\u093e\u0932\u0947\u0902\u0964 \u0917\u0902\u0927\u0915 \u092e\u093f\u091f\u094d\u091f\u0940 \u092e\u0947\u0902 \u0938\u0932\u094d\u092b\u094d\u092f\u0942\u0930\u093f\u0915 \u090f\u0938\u093f\u0921 \u092e\u0947\u0902 \u092c\u0926\u0932\u0915\u0930 pH \u0915\u094b \u0915\u092e \u0915\u0930\u0924\u093e \u0939\u0948\u0964",
                    "general": "\u0909\u0930\u094d\u0935\u0930\u093e \u0936\u0915\u094d\u0924\u093f \u092c\u0928\u093e\u090f \u0930\u0916\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u092b\u0938\u0932 \u091a\u0915\u094d\u0930 \u0914\u0930 \u0939\u0930\u0940 \u0916\u093e\u0926 \u0915\u093e \u0928\u093f\u092f\u092e\u093f\u0924 \u0909\u092a\u092f\u094b\u0917 \u0915\u0930\u0947\u0902."
                }
            }

            cl = _crops.get(lang, _crops["en"])
            crops = cl.get(req.texture, cl["loamy"])
            sl = _sl.get(lang, _sl["en"])
            dt = _def_t.get(lang, _def_t["en"])
            tps = _tips.get(lang, _tips["en"])

            defs = [ "- " + _ph_desc[lang][ph_s] ]
            if n_s != "optimal": defs.append("- " + dt["N"].format(s=sl[n_s], v=req.n))
            if p_s != "optimal": defs.append("- " + dt["P"].format(s=sl[p_s], v=req.p))
            if k_s != "optimal": defs.append("- " + dt["K"].format(s=sl[k_s], v=req.k))
            def_text = "\n".join(defs)

            # Build 3 actionable tips
            tip1 = tps["organic"]
            
            # Tip 2: Find lowest nutrient to correct
            tip2 = tps["general"]
            if n_s != "optimal" or p_s != "optimal" or k_s != "optimal":
                if k_s == "deficient": tip2 = tps["K"]
                elif p_s == "deficient": tip2 = tps["P"]
                elif n_s == "deficient": tip2 = tps["N"]
                elif k_s == "low": tip2 = tps["K"]
                elif p_s == "low": tip2 = tps["P"]
                elif n_s == "low": tip2 = tps["N"]

            # Tip 3: pH correction
            tip3 = tps["general"]
            if ph_s == "acidic": tip3 = tps["lime"]
            elif ph_s == "alkaline": tip3 = tps["gypsum"]

            response_text = f"""TOP 3 CROPS:
- {crops[0][0]} — {crops[0][1]}%
- {crops[1][0]} — {crops[1][1]}%
- {crops[2][0]} — {crops[2][1]}%

DEFICIENCIES:
{def_text}

IMPROVEMENT PLAN:
1. {tip1}
2. {tip2}
3. {tip3}"""

            words = response_text.split(" ")
            for i in range(0, len(words), 3):
                text_chunk = " ".join(words[i:i+3]) + " "
                data = {"type": "content_block_delta", "delta": {"text": text_chunk}}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)
                
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")





# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)