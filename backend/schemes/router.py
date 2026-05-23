# =============================================================================
# AgriGPT — Government Schemes Q&A
# schemes/router.py  (Updated — Groq error handling)
# =============================================================================

import json
import asyncio
import logging
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timezone

from auth.db import chat_history_col
from auth.utils import decode_token
from schemes.static_kb import SCHEMES_KB

router = APIRouter(prefix="/schemes", tags=["Government Schemes Q&A"])
logger = logging.getLogger(__name__)


class SchemeAskRequest(BaseModel):
    question: str  = Field(..., min_length=3, max_length=500)
    state   : Optional[str]                     = Field(None, max_length=60)
    language: Optional[Literal["en","hi","te"]] = Field("en")


@router.post("/ask")
async def schemes_ask(
    req          : SchemeAskRequest,
    authorization: str = Header(default=""),
):
    try:
        from schemes.rag_engine import ask

        result = await asyncio.wait_for(
            asyncio.to_thread(
                ask,
                req.question.strip(),
                (req.state or "").strip(),
                req.language or "en",
            ),
            timeout=30.0,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Request timed out after 30s. Please try again.",
        )
    except json.JSONDecodeError as e:
        logger.error("JSON parse error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="AI returned an unparseable response. Please try again.",
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        err = str(e)
        # Groq rate limit errors
        if "rate_limit_exceeded" in err or "429" in err or "quota" in err.lower():
            raise HTTPException(
                status_code=429,
                detail="Groq API rate limit exceeded. Please try again in a minute.",
            )
        # Groq auth errors
        if "invalid_api_key" in err or "401" in err or "authentication" in err.lower():
            raise HTTPException(
                status_code=503,
                detail="Invalid GROQ_API_KEY. Please check your Render environment variables.",
            )
        logger.error("Schemes ask error: %s", err)
        raise HTTPException(status_code=500, detail=f"Error: {err}")

    # Save to chat history (best-effort)
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        user_id = decode_token(authorization.split(" ", 1)[1])
    if user_id:
        try:
            try:
                uid = ObjectId(user_id)
            except Exception:
                uid = user_id
            chat_history_col().insert_one({
                "user_id"   : uid,
                "agent"     : "scheme",
                "query"     : req.question.strip(),
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass

    return result


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


@router.get("/health")
async def schemes_health():
    from schemes import rag_engine as re
    return {
        "status" : "healthy" if re._llm is not None else "not_loaded",
        "model"  : re.LLM_MODEL,
        "loaded" : re._engine_loaded,
        "provider": "Groq",
    }