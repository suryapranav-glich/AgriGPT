# =============================================================================
# AgriGPT — FastAPI Server  (updated: Feature 3 Fertilizer added)
# Run: python app.py
# =============================================================================

import os
import io
import sys

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
        print(f"[AgriGPT] ⚠  Fertilizer RAG skipped: {e}")


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
# RUN
# =============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)