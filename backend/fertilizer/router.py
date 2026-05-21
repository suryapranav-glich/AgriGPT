# =============================================================================
# AgriGPT — Feature 3: Fertilizer Recommendation Engine
# fertilizer/router.py
#
# FastAPI router — mounted in app.py under prefix "/fertilizer"
#
# Endpoint:
#   POST /fertilizer/recommend
#   Body: FertilizerRequest JSON
#   Returns: full structured recommendation dict
# =============================================================================

import json

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional

from auth.db import chat_history_col
from auth.utils import decode_token
from bson import ObjectId
from datetime import datetime, timezone

from fertilizer.rag_engine import recommend


router = APIRouter(prefix="/fertilizer", tags=["Fertilizer Recommendation"])


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================
class FertilizerRequest(BaseModel):
    crop: str = Field(
        ...,
        min_length=2,
        max_length=80,
        example="Tomato",
        description="Name of the crop (e.g. Tomato, Rice, Wheat, Cotton)",
    )
    soil_type: str = Field(
        ...,
        min_length=2,
        max_length=120,
        example="Red loamy soil",
        description=(
            "Soil type and texture "
            "(e.g. Black cotton, Sandy loam, Red laterite, Alluvial)"
        ),
    )
    growth_stage: str = Field(
        ...,
        min_length=2,
        max_length=120,
        example="Vegetative — 30 days after transplant",
        description=(
            "Current crop growth stage "
            "(e.g. Seedling, Vegetative, Flowering, Fruiting, Maturity)"
        ),
    )
    symptoms: Optional[str] = Field(
        None,
        max_length=400,
        example="Yellowing of older leaves, stunted growth, purple tinge on undersides",
        description="Visible deficiency or problem symptoms (leave blank if none)",
    )


# =============================================================================
# ENDPOINT
# =============================================================================
@router.post("/recommend")
async def fertilizer_recommend(req: FertilizerRequest, authorization: str = Header(default="")):
    """
    Returns a full fertilizer recommendation including:
    - NPK summary (kg/acre)
    - Stage-wise fertilizer schedule with product names & doses
    - Organic alternatives
    - Deficiency-specific treatment (if symptoms provided)
    - Micronutrient advice
    - Cautions & ICAR source reference
    """
    try:
        result = recommend(
            crop         = req.crop.strip(),
            soil_type    = req.soil_type.strip(),
            growth_stage = req.growth_stage.strip(),
            symptoms     = (req.symptoms or "").strip(),
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=(
                "The recommendation engine returned an unparseable response. "
                "Please try again."
            ),
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {e}")

    user_id = None
    if authorization and authorization.startswith("Bearer "):
        user_id = decode_token(authorization.split(" ", 1)[1])
    if user_id:
        try:
            chat_history_col().insert_one({
                "user_id": ObjectId(user_id),
                "agent": "fertilizer",
                "query": f"Fertilizer recommendation for {req.crop} ({req.soil_type})",
                "created_at": datetime.now(timezone.utc)
            })
        except Exception:
            pass

    return {"status": "success", **result}


# =============================================================================
# HEALTH CHECK (fertilizer subsystem)
# =============================================================================
@router.get("/health")
def fertilizer_health():
    from fertilizer import rag_engine as re
    return {
        "status"         : "ok",
        "faiss_loaded"   : re._index is not None,
        "faiss_vectors"  : int(re._index.ntotal) if re._index else 0,
        "static_kb"      : True,
        "llm_model"      : re.LLM_MODEL,
    }
