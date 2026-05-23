# =============================================================================
# backend/chat/router.py
#
# FastAPI router for FarmAI Multilingual Chatbot.
# Exposes endpoints under prefix "/api" (e.g. POST /api/chat).
# =============================================================================

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from bson import ObjectId

from chat.config import settings, LANGUAGE_MAP
from chat.farming_agent import process_query
from auth.db import chat_history_col, sessions_col, messages_col
from auth.utils import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


from typing import Optional

# ── Request / Response schemas ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")
    image_base64: Optional[str] = None
    file_base64: Optional[str] = None
    file_name: Optional[str] = None
    override_lang: Optional[str] = ""


class ChatResponse(BaseModel):
    response: str
    detected_language: str        # ISO 639-1 code, e.g. "te"
    language_name: str            # Human readable, e.g. "Telugu"
    agent_type: str               # "disease" | "market" | "general" | "soil"
    sources: list[str]
    english_query: str            # Debug: what the model actually received


class LanguageDetectRequest(BaseModel):
    text: str = Field(..., min_length=1)


class LanguageDetectResponse(BaseModel):
    lang_code: str
    lang_name: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/detect-language", response_model=LanguageDetectResponse)
async def detect_lang_endpoint(req: LanguageDetectRequest):
    """Auto-detect the language of provided text."""
    from chat.language_detector import detect_language
    code, name = detect_language(req.text)
    return LanguageDetectResponse(lang_code=code, lang_name=name)


@router.get("/languages")
async def list_languages():
    """Return all supported language codes and names."""
    return {"languages": LANGUAGE_MAP}


@router.get("/sessions")
async def list_sessions(authorization: str = Header(default="")):
    """List all chat sessions for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.split(" ", 1)[1]
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        parsed_user_id = user_id
        try:
            parsed_user_id = ObjectId(user_id)
        except Exception:
            pass

        # Build flexible user filter matching both ObjectId and string formats
        conditions = [{"user_id": parsed_user_id}]
        if isinstance(parsed_user_id, ObjectId):
            conditions.append({"user_id": str(parsed_user_id)})
        else:
            try:
                conditions.append({"user_id": ObjectId(parsed_user_id)})
            except Exception:
                pass

        merged_sessions = {}

        # 1. Fetch from sessions_col
        try:
            sessions = list(sessions_col().find({
                "$or": conditions,
                "session_id": {"$exists": True}
            }).sort("last_active", -1))
            for s in sessions:
                s_id = s.get("session_id")
                if not s_id:
                    continue
                created_at_dt = s.get("created_at")
                last_active_dt = s.get("last_active") or created_at_dt
                created_at_str = created_at_dt.isoformat() if created_at_dt else None
                last_active_str = last_active_dt.isoformat() if last_active_dt else None
                
                merged_sessions[s_id] = {
                    "session_id": s_id,
                    "title": s.get("title", "Untitled Chat"),
                    "last_active": last_active_str or created_at_str or datetime.now(timezone.utc).isoformat(),
                    "created_at": created_at_str or last_active_str
                }
        except Exception as e:
            logger.warning("Error fetching from sessions_col: %s", e)

        # 2. Fetch from chat_history_col
        try:
            # We filter for documents that have a response field or belong to a chat agent,
            # ensuring telemetry/activity-only entries like soil analyses or irrigation reports aren't listed as chat history.
            chat_docs = list(chat_history_col().find({
                "$or": conditions,
                "response": {"$exists": True, "$ne": None}
            }).sort("created_at", -1))
            
            for doc in chat_docs:
                s_id = str(doc["_id"])
                
                # Skip if already represented by a multi-turn session
                doc_session_id = doc.get("session_id")
                if doc_session_id and doc_session_id in merged_sessions:
                    continue
                
                # Check for duplicate session based on title and time similarity (for legacy entries)
                created_at_dt = doc.get("created_at")
                if created_at_dt:
                    if created_at_dt.tzinfo is None:
                        created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
                    is_dup = False
                    for s in list(merged_sessions.values()):
                        s_time_str = s.get("created_at") or s.get("last_active")
                        if s_time_str:
                            try:
                                s_time = datetime.fromisoformat(s_time_str.replace("Z", "+00:00"))
                                if s_time.tzinfo is None:
                                    s_time = s_time.replace(tzinfo=timezone.utc)
                                if abs((created_at_dt - s_time).total_seconds()) < 10 and s["title"] == doc.get("query"):
                                    is_dup = True
                                    break
                            except Exception:
                                pass
                    if is_dup:
                        continue

                created_at_str = created_at_dt.isoformat() if created_at_dt else datetime.now(timezone.utc).isoformat()
                merged_sessions[s_id] = {
                    "session_id": s_id,
                    "title": doc.get("query", "Untitled Chat"),
                    "last_active": created_at_str,
                    "created_at": created_at_str
                }
        except Exception as e:
            logger.warning("Error fetching from chat_history_col: %s", e)

        def parse_iso(dt_str):
            try:
                clean_str = dt_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)

        sorted_sessions = sorted(
            merged_sessions.values(),
            key=lambda s: parse_iso(s["last_active"]),
            reverse=True
        )

        return {"sessions": sorted_sessions}
    except Exception as exc:
        logger.error("Failed to list sessions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sessions/{session_id}/messages")
async def list_session_messages(session_id: str, authorization: str = Header(default="")):
    """List all messages for a given session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.split(" ", 1)[1]
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        # Check if session_id is a valid ObjectId and exists in chat_history
        is_object_id = False
        try:
            obj_id = ObjectId(session_id)
            is_object_id = True
        except Exception:
            pass

        if is_object_id:
            chat_doc = chat_history_col().find_one({"_id": obj_id})
            if chat_doc:
                doc_user_id = str(chat_doc.get("user_id"))
                if doc_user_id != str(user_id):
                    raise HTTPException(status_code=403, detail="Not authorized to access this session")

                created_at_dt = chat_doc.get("created_at")
                created_at_str = created_at_dt.isoformat() if created_at_dt else datetime.now(timezone.utc).isoformat()
                assistant_dt_str = (created_at_dt + timedelta(seconds=1)).isoformat() if created_at_dt else created_at_str

                user_msg = {
                    "_id": f"{session_id}_user",
                    "session_id": session_id,
                    "role": "user",
                    "text": chat_doc.get("query", ""),
                    "english_text": chat_doc.get("query", ""),
                    "detected_language": chat_doc.get("detected_language"),
                    "language_name": chat_doc.get("language_name"),
                    "agent_type": None,
                    "sources": [],
                    "created_at": created_at_str,
                    "image_base64": chat_doc.get("image_base64"),
                    "file_base64": chat_doc.get("file_base64"),
                    "file_name": chat_doc.get("file_name"),
                }
                
                assistant_msg = {
                    "_id": f"{session_id}_assistant",
                    "session_id": session_id,
                    "role": "assistant",
                    "text": chat_doc.get("response", ""),
                    "english_text": chat_doc.get("response", ""),
                    "detected_language": chat_doc.get("detected_language"),
                    "language_name": chat_doc.get("language_name"),
                    "agent_type": chat_doc.get("agent"),
                    "sources": chat_doc.get("sources", []),
                    "created_at": assistant_dt_str,
                }
                
                return {"messages": [user_msg, assistant_msg]}

        # Fallback to standard sessions/messages collections
        session = sessions_col().find_one({"session_id": session_id})
        if not session:
            return {"messages": []}

        session_user_id = str(session.get("user_id"))
        if session_user_id != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        messages = list(messages_col().find({"session_id": session_id}).sort("created_at", 1))
        for m in messages:
            m["_id"] = str(m["_id"])
            if "created_at" in m and m["created_at"]:
                m["created_at"] = m["created_at"].isoformat()
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list session messages: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, authorization: str = Header(default="")):
    """
    Main chat endpoint.

    - Accepts message in any of 22 Indian languages (or English).
    - Auto-detects language, queries RAG, generates answer via Gemini.
    - Supports multimodal uploads (images and text/PDF docs).
    - Returns answer translated back into the detected language.
    - Saves the chat conversation into MongoDB sessions/messages collections.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    image_bytes = None
    file_bytes = None

    if req.image_base64:
        try:
            import base64
            img_b64 = req.image_base64
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            image_bytes = base64.b64decode(img_b64)
        except Exception as e:
            logger.error("Failed to decode base64 image: %s", e)

    if req.file_base64:
        try:
            import base64
            fl_b64 = req.file_base64
            if "," in fl_b64:
                fl_b64 = fl_b64.split(",", 1)[1]
            file_bytes = base64.b64decode(fl_b64)
        except Exception as e:
            logger.error("Failed to decode base64 file: %s", e)

    try:
        result = await process_query(
            req.message,
            image_bytes=image_bytes,
            file_bytes=file_bytes,
            file_name=req.file_name,
            override_lang=req.override_lang or "",
        )
    except Exception as exc:
        logger.error("Chat query processing failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}")

    # MongoDB Chat History Logging
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ", 1)[1]
            user_id = decode_token(token)
        except Exception as err:
            logger.warning("Failed to decode token for chat logging: %s", err)

    if user_id:
        try:
            parsed_user_id = user_id
            try:
                parsed_user_id = ObjectId(user_id)
            except Exception:
                pass

            now = datetime.now(timezone.utc)
            session_id = req.session_id or "default"

            # 1. Update or create the session document
            sessions_col().update_one(
                {"session_id": session_id},
                {
                    "$setOnInsert": {
                        "user_id": parsed_user_id,
                        "title": req.message,
                        "language_code": result.detected_language,
                        "language_name": result.language_name,
                        "created_at": now,
                    },
                    "$set": {
                        "last_active": now,
                    },
                    "$inc": {
                        "message_count": 2
                    }
                },
                upsert=True
            )

            # 2. Insert user message document
            user_msg_time = now
            messages_col().insert_one({
                "session_id": session_id,
                "role": "user",
                "text": req.message,
                "english_text": result.english_query,
                "detected_language": result.detected_language,
                "language_name": result.language_name,
                "agent_type": None,
                "sources": [],
                "created_at": user_msg_time,
                "image_base64": req.image_base64,
                "file_base64": req.file_base64,
                "file_name": req.file_name,
            })

            # 3. Insert assistant response document
            ai_msg_time = now + timedelta(seconds=1)
            messages_col().insert_one({
                "session_id": session_id,
                "role": "assistant",
                "text": result.response,
                "english_text": result.english_response,
                "detected_language": result.detected_language,
                "language_name": result.language_name,
                "agent_type": result.agent_type,
                "sources": result.sources,
                "created_at": ai_msg_time
            })

            # 4. Insert legacy chat history document for dashboard compatibility
            chat_history_col().insert_one({
                "user_id": parsed_user_id,
                "session_id": session_id,
                "agent": result.agent_type,
                "query": req.message,
                "response": result.response,
                "detected_language": result.detected_language,
                "language_name": result.language_name,
                "sources": result.sources,
                "created_at": now
            })
            logger.info("Saved chat session and messages to MongoDB for user %s", user_id)
        except Exception as db_err:
            logger.error("Error writing chat history to MongoDB: %s", db_err)

    return ChatResponse(
        response=result.response,
        detected_language=result.detected_language,
        language_name=result.language_name,
        agent_type=result.agent_type,
        sources=result.sources,
        english_query=result.english_query,
    )

