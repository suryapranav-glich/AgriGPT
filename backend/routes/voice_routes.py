import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Form, Header, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from bson import ObjectId

from agents.voice_agent import transcribe_audio, text_to_speech
from auth.db import voice_queries_col
from auth.utils import decode_token

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])

# Allowed audio MIME types from browser MediaRecorder
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/ogg",
    "audio/m4a",
    "audio/aac",
    "application/octet-stream",  # some browsers send this for .webm
}


class TTSRequest(BaseModel):
    text: str
    language: str   # "en" | "te" | "hi"


# ─── Helper ─────────────────────────────────────────────────────────────────

def _save_upload(audio: UploadFile) -> str:
    """Save uploaded audio to a temp file; return its path."""
    suffix = Path(audio.filename).suffix if audio.filename else ".webm"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(audio.file, f)
    return path


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    """
    Step 1 — Accept audio blob, return transcribed text + detected language.
    Frontend calls this first to show the farmer what was heard.
    """
    tmp_path = _save_upload(audio)
    try:
        result = await transcribe_audio(tmp_path)
        return {
            "success":           True,
            "text":              result["text"],
            "detected_language": result["detected_language"],
            "language_name":     result["language_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.post("/speak")
async def speak_text(req: TTSRequest):
    """
    Step 2 — Convert any text to speech in the requested language.
    Returns an MP3 audio file.
    """
    if req.language not in ("en", "te", "hi"):
        raise HTTPException(status_code=400, detail="language must be 'en', 'te', or 'hi'")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    try:
        audio_path = await text_to_speech(req.text, req.language)
        return FileResponse(audio_path, media_type="audio/mpeg", filename="response.mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@router.post("/process")
async def process_voice_query(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    lat: float = Form(None),
    lng: float = Form(None),
    authorization: str = Header(default="")
):
    """
    Full pipeline — Audio in → Whisper STT → Agent Router → gTTS → Audio out.
    Returns MP3 with transcription and agent response in response headers.
    """
    tmp_path = _save_upload(audio)
    try:
        # ── 1. Speech → Text ──────────────────────────────────────────────
        transcription = await transcribe_audio(tmp_path)
        text = transcription["text"]
        lang = transcription["detected_language"]

        if not text:
            raise HTTPException(status_code=422, detail="Could not transcribe audio — please speak clearly.")

        # ── 2. Route to LangGraph agent ───────────────────────────────────
        # Instead of a complex LangGraph router, we use Gemini directly here to answer the voice query
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        system_prompt = f"""You are AgriGPT, a helpful agricultural assistant for farmers in India.
You must answer the user's query in the language: {transcription['language_name']}.
If they ask for market prices, provide a realistic estimated price based on current Indian market trends (e.g. Tomatoes in Guntur are around Rs. 2200 - 2500 per quintal right now).
If they ask for weather, give a realistic short weather forecast.
If they ask for schemes, provide helpful information about PM-Kisan or relevant subsidies.
Keep your answer very concise (2-4 sentences max) because it will be spoken out loud via text-to-speech.
Do NOT use markdown, bold text, or asterisks. Write in plain text."""
        
        if lat is not None and lng is not None:
            system_prompt += f"\n\nContext: The user's current GPS location is Latitude: {lat}, Longitude: {lng}. If they ask something related to 'my location', use these coordinates to provide hyper-local advice."
        
        try:
            llm_res = await model.generate_content_async([system_prompt, f"User Query: {text}"])
            agent_response = llm_res.text.strip()
        except Exception as e:
            print("LLM Error:", e)
            agent_response = f"I understood you asked: '{text}', but I couldn't generate a response."

        # ── 3. Text → Speech ──────────────────────────────────────────────
        audio_path = await text_to_speech(agent_response, lang)

        # ── 4. MongoDB History Storage ────────────────────────────────────
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]
            user_id = decode_token(token)

        if user_id:
            try:
                try:
                    parsed_uid = ObjectId(user_id)
                except Exception:
                    parsed_uid = user_id
                voice_queries_col().insert_one({
                    "user_id": parsed_uid,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "detected_language": lang,
                    "transcript": text,
                    "agent_reply": agent_response,
                    "agent_type": "market",
                    "audio_duration_seconds": 0.0,
                    "tts_served": True
                })
            except Exception as e:
                print("Failed to save voice history to MongoDB:", e)

        # ── 5. Cleanup TTS File ───────────────────────────────────────────
        background_tasks.add_task(os.remove, audio_path)

        import urllib.parse
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename="response.mp3",
            headers={
                # Pass metadata in headers so frontend can display them (URL-encoded for Unicode support)
                "X-Transcribed-Text":  urllib.parse.quote(text.encode("utf-8")),
                "X-Detected-Language": urllib.parse.quote(lang.encode("utf-8")),
                "X-Agent-Response":    urllib.parse.quote(agent_response[:500].encode("utf-8")),
                "Access-Control-Expose-Headers":
                    "X-Transcribed-Text, X-Detected-Language, X-Agent-Response"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/history")
async def get_voice_history(authorization: str = Header(default="")):
    """
    Fetch the last 10 voice queries for the authenticated user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ", 1)[1]
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        parsed_uid = ObjectId(user_id)
    except Exception:
        parsed_uid = user_id

    docs = voice_queries_col().find({
        "$or": [
            {"user_id": parsed_uid},
            {"user_id": user_id}
        ]
    }).sort("timestamp", -1).limit(10)
    
    history = []
    for doc in docs:
        history.append({
            "q": doc.get("transcript", ""),
            "agent": doc.get("agent_type", "market"),
            "t": doc.get("timestamp", "")
        })
    return {"history": history}
