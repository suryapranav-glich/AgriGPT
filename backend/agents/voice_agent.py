import os
import json
import tempfile
from pathlib import Path
import google.generativeai as genai
from gtts import gTTS

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SUPPORTED_LANGUAGES = {
    "en": "English",
    "te": "Telugu",
    "hi": "Hindi"
}

GTTS_LANG_MAP = {
    "en": "en",
    "te": "te",
    "hi": "hi"
}


async def transcribe_audio(audio_file_path: str) -> dict:
    """
    Send audio to Google Gemini API for transcription and language detection.
    """
    # Initialize the model (using a current 2026 model)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()

    # Pass the audio inline to bypass the File API upload/processing delays
    audio_part = {
        "mime_type": "audio/webm",
        "data": audio_data
    }
    
    prompt = '''
    Please listen to this audio and transcribe it accurately.
    Also detect the language spoken.
    Return ONLY a raw JSON object with two keys:
    "text": the transcribed text,
    "language": the detected language code (must be exactly "en", "te", or "hi". If it's something else, try to map it to the closest one or default to "en").
    Do not wrap the JSON in markdown blocks like ```json. Just return the JSON object directly.
    '''
    
    try:
        response = await model.generate_content_async([prompt, audio_part])
        result_text = response.text.strip()
        
        # Clean up the JSON if Gemini accidentally added markdown blocks
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(result_text)
        text = data.get("text", "")
        lang_code = data.get("language", "en").lower()
        
    except Exception as e:
        print(f"Gemini transcription error: {e}")
        text = "Sorry, I couldn't process the audio."
        lang_code = "en"

    if lang_code not in SUPPORTED_LANGUAGES:
        lang_code = "en"

    return {
        "text":              text,
        "detected_language": lang_code,
        "language_name":     SUPPORTED_LANGUAGES[lang_code],
        "whisper_raw_lang":  lang_code
    }


async def text_to_speech(text: str, language_code: str) -> str:
    """
    Convert agent response text to MP3 using gTTS.
    Returns the path of the generated audio file.
    """
    if language_code not in GTTS_LANG_MAP:
        language_code = "en"

    gtts_lang = GTTS_LANG_MAP[language_code]
    tts       = gTTS(text=text, lang=gtts_lang, slow=False)

    # Save to a temp file that persists until explicitly deleted
    out_dir = Path(tempfile.gettempdir()) / "agrigpt_tts"
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / f"response_{language_code}_{os.urandom(4).hex()}.mp3"
    tts.save(str(out_path))

    return str(out_path)
