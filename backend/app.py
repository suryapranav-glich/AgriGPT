# =============================================================================
# AgriGPT — FastAPI Server
# Dual LLM: Groq (text) + Gemini (images/soil analysis)
# Deployed: Backend → Render | Frontend → Vercel (https://agrigpt-xi.vercel.app)
# =============================================================================

import os
import io
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import uvicorn
from fastapi import Header

from auth.db import chat_history_col, disease_diagnoses_col
from auth.utils import decode_token
from bson import ObjectId
from datetime import datetime, timezone

def safe_object_id(uid):
    try:
        return ObjectId(uid)
    except Exception:
        return uid

# ── Routers ───────────────────────────────────────────────────────────────────
from auth.router       import router as auth_router
from dashboard.router  import router as dashboard_router
from fertilizer.router import router as fertilizer_router
from schemes.router    import router as schemes_router
from irrigation.router import router as irrigation_router
from market            import router as market_router
from routes.voice_routes import router as voice_router
from chat.router       import router as chat_router

# ── Resolve paths ─────────────────────────────────────────────────────────────
BASE_DIR     = os.path.join(os.path.dirname(__file__), "saved_models")
WEIGHTS_PATH = os.path.join(BASE_DIR, "agrigpt_production_weights.pth")
CLASSES_PATH = os.path.join(BASE_DIR, "class_names.json")

# ── Feature 1: Disease Detection ──────────────────────────────────────────────
from inference import predict_from_pil

# ── Disease knowledge base ────────────────────────────────────────────────────
from disease_info import DISEASE_INFO, get_disease_info

# ── Confidence threshold ──────────────────────────────────────────────────────
# HF Space returns values like 55.64 (percent). We divide by 100 in /diagnose
# so the effective threshold here is 0.20 = 20% minimum confidence.
# Your HF model returns 55%+ so this will always pass for real predictions.
CONFIDENCE_THRESHOLD = 0.20  # was 0.25 — lowered to handle borderline cases


# =============================================================================
# APP SETUP
# =============================================================================
app = FastAPI(title="AgriGPT API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agrigpt-xi.vercel.app",
        "https://agrigpt-gs4dapeaj-suryas-projects-0a30678c.vercel.app",  # preview deploy
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(fertilizer_router)
app.include_router(schemes_router)
app.include_router(irrigation_router)
app.include_router(market_router)
app.include_router(voice_router)
app.include_router(chat_router)


# =============================================================================
# STARTUP
# =============================================================================
@app.on_event("startup")
async def startup_event():
    print("[AgriGPT] Starting up...")
    print(f"[AgriGPT] HF Space URL: {os.getenv('HF_SPACE_URL', 'https://ssuryapranav-agrimodel-disease.hf.space')}")

    print("[AgriGPT] Building FarmAI FAISS index...")
    try:
        from chat.rag_pipeline import build_index as build_chat_index
        print("[AgriGPT] FarmAI RAG index ready.")
    except Exception as e:
        print(f"[AgriGPT] [WARNING] FarmAI Chat RAG skipped: {e}")

    try:
        from chat.farming_agent import _get_groq_client
        _get_groq_client()
        print("[AgriGPT] Groq client ready (llama-3.1-8b-instant).")
    except Exception as e:
        print(f"[AgriGPT] [WARNING] Groq warmup skipped: {e}")

    try:
        from chat.farming_agent import _get_gemini_model
        _get_gemini_model()
        print("[AgriGPT] Gemini client ready (gemini-2.0-flash).")
    except Exception as e:
        print(f"[AgriGPT] [WARNING] Gemini warmup skipped: {e}")

    print("[AgriGPT] All systems ready.")


# =============================================================================
# HEALTH & HOME
# =============================================================================
@app.get("/health")
def health():
    return {
        "status" : "ok",
        "classes": 38,
        "device" : "cpu",
        "hf_space": os.getenv("HF_SPACE_URL", "https://ssuryapranav-agrimodel-disease.hf.space"),
        "llm": {
            "text" : "Groq / llama-3.1-8b-instant",
            "image": "Gemini / gemini-2.0-flash",
        },
    }


@app.get("/")
def home():
    return {"message": "AgriGPT Backend Running"}


# =============================================================================
# FEATURE 1 — DISEASE DETECTION
# =============================================================================
@app.post("/diagnose")
async def diagnose(
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPG or PNG)")

    contents  = await file.read()
    pil_image = Image.open(io.BytesIO(contents)).convert("RGB")

    # ── Call HF Space via inference.py ────────────────────────────────────────
    result = predict_from_pil(pil_image, top_k=5)

    # ── result["confidence"] is already a PERCENTAGE (e.g. 55.64)
    # ── We normalise to 0-1 only for the threshold comparison
    top_confidence_pct = result["confidence"]           # e.g. 55.64
    top_confidence     = top_confidence_pct / 100.0     # e.g. 0.5564

    top_class      = result["predicted_class"]           # e.g. "Tomato___Late_blight"
    plant_name     = result["plant"]                     # e.g. "Tomato"
    condition_name = result["condition"]                 # e.g. "Late blight"

    # ── Debug log (visible in Render logs) ────────────────────────────────────
    print(f"[/diagnose] plant={plant_name!r}  condition={condition_name!r}  "
          f"confidence={top_confidence_pct}%  threshold={CONFIDENCE_THRESHOLD*100}%")

    # ── Uncertain: HF call failed entirely (confidence == 0) ─────────────────
    if top_confidence_pct == 0.0 or plant_name == "Unknown":
        return {
            "status"            : "uncertain",
            "message"           : (
                "Could not reach the disease detection model. "
                "Please try again — the AI model may be waking up (cold start)."
            ),
            "confidence"        : 0.0,
            "top_predictions"   : [],
            "consult_agronomist": True,
        }

    # ── Uncertain: low confidence real prediction ─────────────────────────────
    if top_confidence < CONFIDENCE_THRESHOLD:
        return {
            "status"            : "uncertain",
            "message"           : (
                f"Model confidence too low ({top_confidence_pct:.1f}%). "
                "Please upload a clearer, close-up leaf photo in good lighting."
            ),
            "confidence"        : round(top_confidence_pct, 1),
            "top_predictions"   : [
                {"class": item["class"], "confidence": item["confidence"]}
                for item in result["top_k"]
            ],
            "consult_agronomist": True,
        }

    # ── Success ───────────────────────────────────────────────────────────────
    info = get_disease_info(top_class)

    response_data = {
        "status"            : "success",
        "plant"             : plant_name,
        "disease"           : condition_name,
        "class_id"          : top_class,
        "confidence"        : round(top_confidence_pct, 1),
        "severity"          : info["severity"],
        "cause"             : info["cause"],
        "organic_treatment" : info["organic"],
        "chemical_treatment": info["chemical"],
        "prevention_tips"   : info["prevention"],
        "consult_agronomist": top_confidence < 0.80,
        "top5"              : [
            {
                "class"     : item["class"].replace("___", " — ").replace("_", " "),
                "confidence": item["confidence"],
            }
            for item in result["top_k"]
        ],
    }

    # ── Save to MongoDB ───────────────────────────────────────────────────────
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        user_id = decode_token(authorization.split(" ", 1)[1])

    if user_id:
        now = datetime.now(timezone.utc)
        try:
            disease_diagnoses_col().insert_one({
                "user_id"          : safe_object_id(user_id),
                "timestamp"        : now.isoformat(),
                "created_at"       : now,
                "updated_at"       : now,
                "disease_detected" : condition_name,
                "disease"          : condition_name,
                "plant"            : plant_name,
                "severity"         : info.get("severity", "none"),
                "confidence"       : float(top_confidence),
                "result"           : f"{plant_name} — {condition_name}",
            })
            chat_history_col().insert_one({
                "user_id"   : safe_object_id(user_id),
                "agent"     : "disease",
                "query"     : f"Uploaded crop photo. Result: {condition_name}",
                "status"    : "answered",
                "created_at": now,
            })
        except Exception as e:
            print(f"[/diagnose] MongoDB save error: {e}")

    return response_data


# =============================================================================
# FEATURE 4 — SOIL HEALTH ANALYSIS
# =============================================================================
from pydantic import BaseModel

class SoilAnalyseRequest(BaseModel):
    ph     : float
    n      : float
    p      : float
    k      : float
    texture: str
    grade  : str
    lang   : str = "en"


@app.post("/soil/analyse")
async def soil_analyse(
    req          : SoilAnalyseRequest,
    authorization: str = Header(default=""),
):
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

    n_status  = "deficient (Very Low)" if req.n < 120 else ("low" if req.n < 180 else "good/optimal")
    p_status  = "deficient (Very Low)" if req.p < 15  else ("low" if req.p < 30  else "good/optimal")
    k_status  = "deficient (Very Low)" if req.k < 100 else ("low" if req.k < 160 else "good/optimal")
    ph_status = "acidic (low)" if req.ph < 6.0 else ("alkaline (high)" if req.ph > 7.5 else "neutral (optimal)")

    prompt = f"""You are AgriGPT's soil health expert for Indian farmers (Telangana/Andhra Pradesh focus).

{lang_instruction}

Soil test values and their evaluated statuses:
- pH: {req.ph} (Status: {ph_status})
- Nitrogen (N): {req.n} kg/ha (Status: {n_status})
- Phosphorus (P): {req.p} kg/ha (Status: {p_status})
- Potassium (K): {req.k} kg/ha (Status: {k_status})
- Soil texture: {req.texture}
- Overall soil grade: {req.grade}

Provide a structured response with EXACTLY these three sections. Keep section headers in English:

TOP 3 CROPS:
List exactly 3 crops best suited for these soil conditions with suitability % (e.g. "Tomato — 92%").
If the soil texture is loamy, prioritize root/tuber crops (Ginger, Turmeric, Sweet Potato, Cassava).

DEFICIENCIES:
List the evaluated status of each parameter (pH and NPK).
State if pH is optimal or problematic. Comment only on low/deficient nutrients.

IMPROVEMENT PLAN:
Give exactly 3 numbered actionable soil improvement tips:
1. Organic matter / carbon building.
2. Correcting specific nutrient deficiencies.
3. pH correction — if acidic use agricultural lime; if alkaline use Elemental Sulfur (NOT gypsum); if optimal give a micro-nutrient tip.

IMPORTANT: Section headers (TOP 3 CROPS, DEFICIENCIES, IMPROVEMENT PLAN) MUST stay in English.
Be concise, practical, and farmer-friendly. No markdown bold, no extra headers."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured. Set it in Render Environment Variables.",
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    async def generate():
        use_fallback = False
        try:
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    data = {
                        "type" : "content_block_delta",
                        "delta": {"text": chunk.text},
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"[Soil Analyse] Gemini streaming failed: {e}. Using fallback.")
            use_fallback = True

        # Log activity
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            user_id = decode_token(authorization.split(" ", 1)[1])
        if user_id:
            try:
                chat_history_col().insert_one({
                    "user_id"   : safe_object_id(user_id),
                    "agent"     : "soil",
                    "query"     : f"Analyzed soil (pH:{req.ph}, N:{req.n}, P:{req.p}, K:{req.k})",
                    "status"    : "answered",
                    "created_at": datetime.now(timezone.utc),
                })
            except Exception:
                pass

        if use_fallback:
            n_s  = "deficient" if req.n < 120 else ("low" if req.n < 180 else "optimal")
            p_s  = "deficient" if req.p < 15  else ("low" if req.p < 30  else "optimal")
            k_s  = "deficient" if req.k < 100 else ("low" if req.k < 160 else "optimal")
            ph_s = "acidic"    if req.ph < 6.0 else ("alkaline" if req.ph > 7.5 else "optimal")

            _crops = {
                "black": [("Cotton", 94), ("Paddy", 88), ("Chilli", 85)],
                "clay" : [("Paddy", 91), ("Maize", 83), ("Sorghum", 78)],
                "sandy": [("Groundnut", 92), ("Chilli", 84), ("Sesame", 79)],
                "loamy": [("Sweet Potato", 92), ("Ginger", 88), ("Tomato", 85)],
            }
            crops = _crops.get(req.texture, _crops["loamy"])

            defs = []
            if ph_s == "acidic":     defs.append(f"- Soil pH is acidic ({req.ph}) — limits nutrient availability.")
            elif ph_s == "alkaline": defs.append(f"- Soil pH is alkaline ({req.ph}) — can lock micronutrients.")
            else:                    defs.append(f"- Soil pH is optimal ({req.ph}) — good for nutrient absorption.")
            if n_s != "optimal": defs.append(f"- Nitrogen (N) is {n_s} ({req.n} kg/ha).")
            if p_s != "optimal": defs.append(f"- Phosphorus (P) is {p_s} ({req.p} kg/ha).")
            if k_s != "optimal": defs.append(f"- Potassium (K) is {k_s} ({req.k} kg/ha).")

            tip2 = "Maintain balanced fertilization."
            if   k_s == "deficient": tip2 = "Apply MOP (Muriate of Potash) to correct Potassium deficiency."
            elif p_s == "deficient": tip2 = "Apply SSP or DAP to correct Phosphorus deficiency."
            elif n_s == "deficient": tip2 = "Apply Urea in split doses to correct Nitrogen deficiency."
            elif k_s == "low":       tip2 = "Apply MOP to improve Potassium levels."
            elif p_s == "low":       tip2 = "Apply SSP to improve Phosphorus levels."
            elif n_s == "low":       tip2 = "Apply Urea to improve Nitrogen levels."

            tip3 = "Maintain crop rotation and green manuring to preserve fertility."
            if   ph_s == "acidic":   tip3 = "Apply agricultural lime to neutralize soil acidity."
            elif ph_s == "alkaline": tip3 = "Apply Elemental Sulfur (not gypsum) to reduce alkaline pH."

            fallback_text = f"""TOP 3 CROPS:
- {crops[0][0]} — {crops[0][1]}%
- {crops[1][0]} — {crops[1][1]}%
- {crops[2][0]} — {crops[2][1]}%

DEFICIENCIES:
{chr(10).join(defs)}

IMPROVEMENT PLAN:
1. Add 5-10 tonnes/ha of well-decomposed FYM or compost to build organic carbon.
2. {tip2}
3. {tip3}"""

            words = fallback_text.split(" ")
            for i in range(0, len(words), 3):
                chunk_text = " ".join(words[i:i + 3]) + " "
                data = {"type": "content_block_delta", "delta": {"text": chunk_text}}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)