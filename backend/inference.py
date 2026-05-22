# =============================================================================
# AgriGPT — Feature 1: Crop Disease Detection
# inference.py — Lightweight version calling Hugging Face Space API
# =============================================================================

import os
import io
import re
import requests
from PIL import Image

# =============================================================================
# CONFIG
# =============================================================================
HF_SPACE_URL = "https://ssuryapranav-agrimodel-disease.hf.space"

# Mock variables to preserve compatibility with existing app.py code
DEVICE = "cpu"
WEIGHTS_PATH = ""
CLASSES_PATH = ""

def load_model(
    weights_path: str = "",
    classes_path: str = "",
    device: str = "cpu",
):
    """
    Mock model loader. Returns dummy variables to keep app.py compatible
    without loading heavy PyTorch models locally.
    """
    print("[AgriGPT] Using Hugging Face Space for disease detection.")
    return None, None, "cpu"


def predict_from_pil(
    pil_image: Image.Image,
    model = None,
    class_names = None,
    device = None,
    top_k: int = 5,
) -> dict:
    """
    Sends the PIL Image to the Hugging Face Space running Gradio and parses the result.
    """
    try:
        # Convert PIL Image to JPEG bytes
        img_byte_arr = io.BytesIO()
        pil_image.convert("RGB").save(img_byte_arr, format='JPEG')
        image_bytes = img_byte_arr.getvalue()
        
        # 1. Upload file to Gradio upload endpoint
        upload_url = f"{HF_SPACE_URL}/upload"
        files = {"files": ("image.jpg", image_bytes, "image/jpeg")}
        response = requests.post(upload_url, files=files, timeout=15.0)
        if response.status_code != 200:
            raise Exception(f"Failed to upload image to Hugging Face: {response.text}")
        
        uploaded_files = response.json()
        if not uploaded_files:
            raise Exception("No file returned from Hugging Face upload")
        file_path = uploaded_files[0]
        
        # 2. Call prediction endpoint
        predict_url = f"{HF_SPACE_URL}/gradio_api/predict"
        payload = {
            "data": [
                {"path": file_path, "meta": {"_type": "gradio.FileData"}}
            ],
            "fn_index": 0
        }
        pred_response = requests.post(predict_url, json=payload, timeout=20.0)
        if pred_response.status_code != 200:
            raise Exception(f"Prediction failed on Hugging Face: {pred_response.text}")
            
        result_data = pred_response.json()
        if "data" in result_data and len(result_data["data"]) > 0:
            text = result_data["data"][0]
            
            # Parse the formatted string returned by the Gradio space
            plant = "Unknown"
            condition = "Unknown"
            confidence = 100.0
            
            # Match "Plant: Tomato"
            plant_match = re.search(r"Plant:\s*(.*)", text)
            # Match "Condition: Late blight"
            cond_match = re.search(r"Condition:\s*(.*)", text)
            # Match "Confidence: 98.74%"
            conf_match = re.search(r"Confidence:\s*([\d.]+)", text)
            
            if plant_match and cond_match:
                plant = plant_match.group(1).strip()
                condition = cond_match.group(1).strip()
            else:
                # Match fallback format "Diagnosis: Tomato___healthy"
                diag_match = re.search(r"Diagnosis:\s*(.*)", text)
                if diag_match:
                    diag = diag_match.group(1).strip()
                    if "___" in diag:
                        plant, condition = diag.split("___", 1)
                        condition = condition.replace("_", " ")
                    else:
                        plant = diag
                        condition = diag

            if conf_match:
                try:
                    confidence = float(conf_match.group(1).strip())
                except ValueError:
                    pass
            
            predicted_class = f"{plant}___{condition.replace(' ', '_')}"
            is_healthy = "healthy" in condition.lower()
            
            return {
                "predicted_class": predicted_class,
                "confidence": confidence,
                "plant": plant,
                "condition": condition,
                "is_healthy": is_healthy,
                "top_k": [
                    {
                        "rank": 1,
                        "class": predicted_class,
                        "confidence": confidence
                    }
                ]
            }
        raise Exception("Malformed prediction response from Hugging Face")
        
    except Exception as e:
        print(f"[AgriGPT HF API] Error calling Hugging Face Space: {e}")
        # Return fallback dictionary to keep application running
        return {
            "predicted_class": "Unknown___Unknown",
            "confidence": 0.0,
            "plant": "Unknown",
            "condition": "Unknown",
            "is_healthy": False,
            "top_k": []
        }


def predict_disease(
    image_path: str,
    model = None,
    class_names = None,
    device = None,
    top_k: int = 5,
) -> dict:
    """
    Run inference on a single image file path.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    image = Image.open(image_path).convert("RGB")
    return predict_from_pil(image, model, class_names, device, top_k)


# Standalone CLI test support
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AgriGPT — Hugging Face API Disease Inference")
    parser.add_argument("--image", type=str, required=True, help="Path to leaf image (JPG/PNG)")
    args = parser.parse_args()

    result = predict_disease(args.image)
    print(f"\n=======================================================")
    print(f"  Plant     : {result['plant']}")
    print(f"  Condition : {result['condition']}")
    print(f"  Healthy   : {'✅ Yes' if result['is_healthy'] else '❌ No'}")
    print(f"  Confidence: {result['confidence']}%")
    print(f"=======================================================\n")