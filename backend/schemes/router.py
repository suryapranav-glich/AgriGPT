# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/router.py
#
# Mounted in app.py under prefix "/schemes"
#
# Endpoints:
#   POST /schemes/ask      → LangChain RetrievalQA answer with source highlights
#   GET  /schemes/list     → scheme list for frontend cards
#   GET  /schemes/health   → subsystem health
# =============================================================================

import json
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Literal
from auth.db import chat_history_col
from auth.utils import decode_token
from bson import ObjectId
from datetime import datetime, timezone

# from schemes.rag_engine import ask
from schemes.static_kb  import SCHEMES_KB

router = APIRouter(prefix="/schemes", tags=["Government Schemes Q&A"])


# =============================================================================
# REQUEST MODEL
# =============================================================================
class SchemeAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length = 3,
        max_length = 500,
        example    = "PM-KISAN ke liye kaise apply karein Telangana mein?",
    )
    state: Optional[str] = Field(
        None,
        max_length = 60,
        example    = "Telangana",
        description= "Farmer's state for state-specific answers (Telangana / Andhra Pradesh)",
    )
    language: Optional[Literal["en", "hi", "te"]] = Field(
        "en",
        description="Response language: 'en' for English, 'hi' for Hindi, 'te' for Telugu",
    )


# =============================================================================
# POST /schemes/ask
# =============================================================================
@router.post("/ask")
async def schemes_ask(req: SchemeAskRequest, authorization: str = Header(default="")):
    """
    LangChain RetrievalQA — Government Schemes Q&A.
    Supports English, Hindi and Telugu. State-specific for Telangana & AP.
    Returns structured answer with source_highlights (file, page, snippet).
    """
    try:
        from schemes.rag_engine import ask
        result = ask(
            question = req.question.strip(),
            state    = (req.state or "").strip(),
            language = req.language or "en",
        )

        user_id = None
        if authorization and authorization.startswith("Bearer "):
            user_id = decode_token(authorization.split(" ", 1)[1])
        if user_id:
            try:
                parsed_uid = ObjectId(user_id)
            except Exception:
                parsed_uid = user_id
            try:
                chat_history_col().insert_one({
                    "user_id": parsed_uid,
                    "agent": "scheme",
                    "query": req.question.strip(),
                    "created_at": datetime.now(timezone.utc)
                })
            except Exception:
                pass

        return result
    except json.JSONDecodeError:
        raise HTTPException(
            status_code = 500,
            detail      = "Answer engine returned an unparseable response. Please try again.",
        )
    except EnvironmentError as ee:
        raise HTTPException(
            status_code = 500,
            detail      = str(ee),
        )
    except Exception as e:
        err_str = str(e)
        # Detect Gemini API rate-limit / quota exhausted
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
            import re
            # Try to extract retry delay from the error message
            delay_match = re.search(r"retry in (\d+)", err_str)
            delay_msg = f" Please retry in {delay_match.group(1)} seconds." if delay_match else " Please try again in a few minutes."
            raise HTTPException(
                status_code = 429,
                detail      = f"Gemini API quota exceeded (free tier: 20 req/day).{delay_msg}",
            )
        raise HTTPException(
            status_code = 500,
            detail      = f"RAG Query Engine failed: {err_str}",
        )


# =============================================================================
# GET /schemes/list
# =============================================================================
@router.get("/list")
async def schemes_list(state: Optional[str] = None):
    """
    Returns list of schemes in KB, optionally filtered by state name.
    """
    if not state:
        return SCHEMES_KB

    st = state.lower().strip()
    from schemes.static_kb import STATE_ALIASES
    st_mapped = STATE_ALIASES.get(st, st)

    filtered = []
    for s in SCHEMES_KB:
        if "all" in s["states"] or any(st_mapped in x for x in s["states"]):
            filtered.append(s)
    return filtered


# =============================================================================
# GET /schemes/health
# =============================================================================
@router.get("/health")
async def schemes_health():
    """
    Checks if LLM and index are reachable.
    """
    from schemes import rag_engine
    return {
        "status"      : "healthy" if rag_engine._llm is not None else "degraded",
        "vector_db"   : rag_engine._vector_db,
        "model"       : rag_engine.LLM_MODEL,
        "embeddings"  : rag_engine.EMBED_MODEL,
    }
