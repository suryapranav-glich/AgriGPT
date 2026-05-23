# =============================================================================
# AgriGPT — Feature 1: Crop Disease Detection
# inference.py — Calls Hugging Face Space Gradio API
# =============================================================================

import os
import io
import re
import json
import requests
from PIL import Image

# =============================================================================
# CONFIG
# =============================================================================
HF_SPACE_URL = os.getenv(
    "HF_SPACE_URL",
    "https://ssuryapranav-agrimodel-disease.hf.space"
).strip().rstrip("/")

DEVICE       = "cpu"
WEIGHTS_PATH = ""
CLASSES_PATH = ""


def load_model(weights_path="", classes_path="", device="cpu"):
    """Mock loader — keeps app.py compatible without loading PyTorch locally."""
    print(f"[AgriGPT] Using Hugging Face Space: {HF_SPACE_URL}")
    class_names = []
    if classes_path and os.path.exists(classes_path):
        try:
            with open(classes_path, "r", encoding="utf-8") as f:
                class_names = json.load(f)
        except Exception as e:
            print(f"[AgriGPT] Could not load class_names.json: {e}")
    return None, class_names, "cpu"


# =============================================================================
# MAIN PREDICTION
# =============================================================================
def predict_from_pil(
    pil_image: Image.Image,
    model=None,
    class_names=None,
    device=None,
    top_k: int = 5,
) -> dict:
    """
    Sends PIL Image to HuggingFace Gradio Space and returns structured result.
    Tries two API styles (new /gradio_api/call + legacy /run/predict).
    Falls back gracefully on any network or parse error.
    """
    try:
        # ── Convert PIL → JPEG bytes ──────────────────────────────────────────
        buf = io.BytesIO()
        pil_image.convert("RGB").save(buf, format="JPEG", quality=92)
        image_bytes = buf.getvalue()

        # ── Strategy 1: New Gradio 4.x queue API ─────────────────────────────
        result = _call_gradio_queue_api(image_bytes)
        if result:
            return result

        # ── Strategy 2: Legacy /run/predict with upload ───────────────────────
        result = _call_gradio_legacy_api(image_bytes)
        if result:
            return result

        # ── Strategy 3: Direct /api/predict (some spaces) ────────────────────
        result = _call_gradio_direct_api(image_bytes)
        if result:
            return result

        raise Exception("All Gradio API strategies failed")

    except Exception as e:
        print(f"[AgriGPT HF] predict_from_pil error: {e}")
        return _error_result()


# =============================================================================
# API STRATEGY 1 — Gradio 4.x /gradio_api/call (event-stream)
# =============================================================================
def _call_gradio_queue_api(image_bytes: bytes) -> dict | None:
    try:
        # Step 1: Upload
        upload_url = f"{HF_SPACE_URL}/gradio_api/upload"
        upload_resp = requests.post(
            upload_url,
            files={"files": ("leaf.jpg", image_bytes, "image/jpeg")},
            timeout=20,
        )
        if upload_resp.status_code != 200:
            print(f"[HF Queue] Upload failed: {upload_resp.status_code}")
            return None

        uploaded = upload_resp.json()
        # Gradio returns list of file paths or dicts
        if isinstance(uploaded, list) and uploaded:
            file_ref = uploaded[0]
        else:
            print(f"[HF Queue] Unexpected upload response: {uploaded}")
            return None

        # Step 2: Queue call
        call_url = f"{HF_SPACE_URL}/gradio_api/call/predict"
        payload  = {
            "data": [
                {"path": file_ref} if isinstance(file_ref, str)
                else file_ref
            ]
        }
        call_resp = requests.post(call_url, json=payload, timeout=20)
        if call_resp.status_code != 200:
            print(f"[HF Queue] Call failed: {call_resp.status_code} — {call_resp.text[:200]}")
            return None

        event_id = call_resp.json().get("event_id")
        if not event_id:
            print(f"[HF Queue] No event_id returned")
            return None

        # Step 3: Poll result stream
        result_url = f"{HF_SPACE_URL}/gradio_api/call/predict/{event_id}"
        result_resp = requests.get(result_url, timeout=30, stream=True)
        text_output = ""
        for line in result_resp.iter_lines(decode_unicode=True):
            if line.startswith("data:"):
                raw = line[5:].strip()
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and parsed:
                        text_output = str(parsed[0])
                        break
                except Exception:
                    continue

        if text_output:
            print(f"[HF Queue] Raw output: {text_output[:200]}")
            return _parse_hf_text(text_output)

    except Exception as e:
        print(f"[HF Queue] Exception: {e}")
    return None


# =============================================================================
# API STRATEGY 2 — Legacy Gradio /upload + /run/predict
# =============================================================================
def _call_gradio_legacy_api(image_bytes: bytes) -> dict | None:
    try:
        # Upload
        upload_url  = f"{HF_SPACE_URL}/upload"
        upload_resp = requests.post(
            upload_url,
            files={"files": ("leaf.jpg", image_bytes, "image/jpeg")},
            timeout=20,
        )
        if upload_resp.status_code != 200:
            return None

        uploaded = upload_resp.json()
        if not uploaded:
            return None
        file_path = uploaded[0] if isinstance(uploaded, list) else uploaded

        # Predict
        predict_url = f"{HF_SPACE_URL}/run/predict"
        payload = {
            "data": [
                {"path": file_path, "meta": {"_type": "gradio.FileData"}}
                if isinstance(file_path, str)
                else file_path
            ],
            "fn_index": 0,
        }
        pred_resp = requests.post(predict_url, json=payload, timeout=25)
        if pred_resp.status_code != 200:
            print(f"[HF Legacy] Predict failed: {pred_resp.status_code}")
            return None

        data = pred_resp.json().get("data", [])
        if data:
            print(f"[HF Legacy] Raw output: {str(data[0])[:200]}")
            return _parse_hf_text(str(data[0]))

    except Exception as e:
        print(f"[HF Legacy] Exception: {e}")
    return None


# =============================================================================
# API STRATEGY 3 — /api/predict with base64 (some Gradio spaces)
# =============================================================================
def _call_gradio_direct_api(image_bytes: bytes) -> dict | None:
    try:
        import base64
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        predict_url = f"{HF_SPACE_URL}/api/predict"
        payload = {
            "data": [f"data:image/jpeg;base64,{b64}"],
            "fn_index": 0,
        }
        resp = requests.post(predict_url, json=payload, timeout=25)
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        if data:
            print(f"[HF Direct] Raw output: {str(data[0])[:200]}")
            return _parse_hf_text(str(data[0]))
    except Exception as e:
        print(f"[HF Direct] Exception: {e}")
    return None


# =============================================================================
# PARSER — handles both output formats from your HF Space
# =============================================================================
def _parse_hf_text(text: str) -> dict | None:
    """
    Parses HF Space output. Handles two formats:

    Format A (emoji lines):
        🌿 Plant: Tomato
        🔵 Condition: Late blight
        ✅ Confidence: 55.64%

    Format B (plain):
        Plant: Tomato
        Condition: Late blight
        Confidence: 55.64%

    Format C (class string):
        Diagnosis: Tomato___Late_blight
        Confidence: 55.64%
    """
    if not text or not text.strip():
        return None

    plant      = None
    condition  = None
    confidence = None

    # ── Format A/B: Plant + Condition lines ───────────────────────────────────
    plant_match = re.search(r"Plant[:\s]+([A-Za-z][^\n\r✅🌿🔵✔️\U0001F7E2\U0001F535]*)", text)
    cond_match  = re.search(r"Condition[:\s]+([A-Za-z][^\n\r✅🌿🔵✔️\U0001F7E2\U0001F535]*)", text)
    conf_match  = re.search(r"Confidence[:\s]+([\d.]+)\s*%?", text)

    if plant_match:
        plant = plant_match.group(1).strip().rstrip(".,;")
    if cond_match:
        condition = cond_match.group(1).strip().rstrip(".,;")
    if conf_match:
        try:
            confidence = float(conf_match.group(1))
        except ValueError:
            pass

    # ── Format C: Diagnosis: Plant___Condition ────────────────────────────────
    if not plant or not condition:
        diag_match = re.search(r"Diagnosis[:\s]+([A-Za-z_]+)", text)
        if diag_match:
            diag = diag_match.group(1).strip()
            if "___" in diag:
                plant, raw_cond = diag.split("___", 1)
                condition = raw_cond.replace("_", " ").strip()
            else:
                plant     = diag
                condition = diag

    # ── Validation ────────────────────────────────────────────────────────────
    if not plant or not condition:
        print(f"[HF Parser] Could not parse plant/condition from: {text[:300]}")
        return None

    confidence  = confidence if confidence is not None else 85.0
    is_healthy  = "healthy" in condition.lower()
    pred_class  = f"{plant}___{condition.replace(' ', '_')}"

    return {
        "predicted_class": pred_class,
        "confidence"     : confidence,
        "plant"          : plant,
        "condition"      : condition,
        "is_healthy"     : is_healthy,
        "top_k"          : [{"rank": 1, "class": pred_class, "confidence": confidence}],
    }


def _error_result() -> dict:
    """Returned when ALL strategies fail — triggers 'uncertain' in app.py."""
    return {
        "predicted_class": "Unknown___Unknown",
        "confidence"     : 0.0,
        "plant"          : "Unknown",
        "condition"      : "Unknown",
        "is_healthy"     : False,
        "top_k"          : [],
    }


# =============================================================================
# FILE-PATH ENTRY POINT (used by CLI)
# =============================================================================
def predict_disease(
    image_path: str,
    model=None,
    class_names=None,
    device=None,
    top_k: int = 5,
) -> dict:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    image = Image.open(image_path).convert("RGB")
    return predict_from_pil(image, model, class_names, device, top_k)


# =============================================================================
# CLI TEST
# =============================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AgriGPT Disease Inference — HF Space")
    parser.add_argument("--image", required=True, help="Path to leaf image")
    args = parser.parse_args()

    r = predict_disease(args.image)
    print(f"\n{'='*55}")
    print(f"  Plant     : {r['plant']}")
    print(f"  Condition : {r['condition']}")
    print(f"  Healthy   : {'✅ Yes' if r['is_healthy'] else '❌ No'}")
    print(f"  Confidence: {r['confidence']}%")
    print(f"{'='*55}\n")