# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/router.py  (Fixed v2 — async safe, timeout, better errors)
# =============================================================================

import json
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Literal
from auth.db import chat_history_col
from auth.utils import decode_token
from bson import ObjectId
from datetime import datetime, timezone

from schemes.static_kb import SCHEMES_KB

router = APIRouter(prefix="/schemes", tags=["Government Schemes Q&A"])
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST MODEL
# =============================================================================
class SchemeAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    state: Optional[str] = Field(None, max_length=60)
    language: Optional[Literal["en", "hi", "te"]] = Field("en")


# =============================================================================
# POST /schemes/ask
# =============================================================================
@router.post("/ask")
async def schemes_ask(
    req: SchemeAskRequest,
    authorization: str = Header(default="")
):
    """
    Government Schemes Q&A endpoint.
    Runs the sync Gemini call in a thread so it doesn't block FastAPI's event loop.
    """
    try:
        from schemes.rag_engine import ask

        # ✅ Run sync function in thread executor — prevents blocking the event loop
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ask(
                    question=req.question.strip(),
                    state=(req.state or "").strip(),
                    language=req.language or "en",
                )
            ),
            timeout=30.0  # 30 second hard timeout
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Request timed out. The AI is taking too long. Please try again."
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Answer engine returned an unparseable response. Please try again."
        )
    except EnvironmentError as ee:
        raise HTTPException(status_code=503, detail=str(ee))
    except Exception as e:
        err_str = str(e)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
            import re as _re
            delay_match = _re.search(r"retry in (\d+)", err_str)
            delay_msg = f" Retry in {delay_match.group(1)}s." if delay_match else " Try again in a few minutes."
            raise HTTPException(
                status_code=429,
                detail=f"Gemini API quota exceeded (free tier).{delay_msg}"
            )
        logger.error("Schemes ask error: %s", err_str)
        raise HTTPException(status_code=500, detail=f"Query failed: {err_str}")

    # Save to chat history (non-blocking, best-effort)
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        user_id = decode_token(authorization.split(" ", 1)[1])
    if user_id:
        try:
            try:
                parsed_uid = ObjectId(user_id)
            except Exception:
                parsed_uid = user_id
            chat_history_col().insert_one({
                "user_id"   : parsed_uid,
                "agent"     : "scheme",
                "query"     : req.question.strip(),
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass

    return result


# =============================================================================
# GET /schemes/list
# =============================================================================
@router.get("/list")
async def schemes_list(state: Optional[str] = None):
    if not state:
        return SCHEMES_KB
    st = state.lower().strip()
    from schemes.static_kb import STATE_ALIASES
    st_mapped = STATE_ALIASES.get(st, st)
    return [
        s for s in SCHEMES_KB
        if "all" in s["states"] or any(st_mapped in x for x in s["states"])
    ]


# =============================================================================
# GET /schemes/health
# =============================================================================
@router.get("/health")
async def schemes_health():
    from schemes import rag_engine
    return {
        "status"   : "healthy" if rag_engine._llm is not None else "not_loaded",
        "vector_db": rag_engine._vector_db,
        "model"    : rag_engine.LLM_MODEL,
        "loaded"   : rag_engine._engine_loaded,
    }