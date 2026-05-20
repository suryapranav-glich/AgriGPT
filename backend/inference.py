# =============================================================================
# AgriGPT — Feature 1: Crop Disease Detection
# inference.py — matches train.py EfficientNet-B4 architecture exactly
#
# Standalone usage:
#   python inference.py --image leaf.jpg
#
# As a module (called by app.py):
#   from inference import load_model, predict_disease
# =============================================================================

import os
import json
import argparse
import torch
import torch.nn as nn
from torchvision import transforms, models
from torchvision.models import EfficientNet_B4_Weights
from PIL import Image


# =============================================================================
# CONFIG — must match train.py exactly
# =============================================================================
IMAGE_SIZE   = 320
DROPOUT      = 0.4
WEIGHTS_PATH = "agrigpt_production_weights.pth"
CLASSES_PATH = "class_names.json"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# =============================================================================
# 1. SAME VALIDATION TRANSFORM used in train.py
#    train.py val_tf: Resize(size+32) → CenterCrop(size) → ToTensor → Normalize
# =============================================================================
inference_transform = transforms.Compose([
    transforms.Resize(IMAGE_SIZE + 32),        # 352
    transforms.CenterCrop(IMAGE_SIZE),          # 320×320
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


# =============================================================================
# 2. MODEL — EfficientNet-B4 with the EXACT classifier head from train.py
#    model.classifier = nn.Sequential(
#        nn.Dropout(0.4),
#        nn.Linear(1792, 512),
#        nn.ReLU(),
#        nn.Dropout(0.2),
#        nn.Linear(512, num_classes),
#    )
# =============================================================================
def build_model(num_classes: int) -> nn.Module:
    model = models.efficientnet_b4(weights=None)   # no pretrained weights needed
    in_feat = model.classifier[1].in_features      # 1792
    model.classifier = nn.Sequential(
        nn.Dropout(p=DROPOUT, inplace=True),
        nn.Linear(in_feat, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.2),
        nn.Linear(512, num_classes),
    )
    return model


def load_model(
    weights_path: str = WEIGHTS_PATH,
    classes_path: str = CLASSES_PATH,
    device: str = DEVICE,
):
    """
    Load class names + model weights.
    Returns (model, class_names, device).
    Called once at FastAPI startup.
    """
    # -- class names --
    if not os.path.exists(classes_path):
        raise FileNotFoundError(
            f"class_names.json not found at '{classes_path}'.\n"
            "Make sure it was saved by train.py (it is saved automatically)."
        )
    with open(classes_path) as f:
        class_names = json.load(f)
    num_classes = len(class_names)
    print(f"[AgriGPT] {num_classes} classes loaded from {classes_path}")

    # -- model --
    if not os.path.exists(weights_path):
        raise FileNotFoundError(
            f"Weights not found at '{weights_path}'.\n"
            "Download agrigpt_production_weights.pth from your training run."
        )
    model = build_model(num_classes)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.to(device)
    model.eval()
    print(f"[AgriGPT] Model loaded on {device}  <- {weights_path}")
    return model, class_names, device


# =============================================================================
# 3. PREDICT
# =============================================================================
def predict_disease(
    image_path: str,
    model: nn.Module,
    class_names: list,
    device: str,
    top_k: int = 5,
) -> dict:
    """
    Run inference on a single image file path.

    Returns:
    {
        "predicted_class" : "Tomato___Late_blight",
        "confidence"      : 98.74,
        "plant"           : "Tomato",
        "condition"       : "Late blight",
        "is_healthy"      : False,
        "top_k"           : [
            {"rank": 1, "class": "Tomato___Late_blight",  "confidence": 98.74},
            {"rank": 2, "class": "Tomato___Early_blight", "confidence":  0.81},
            ...
        ]
    }
    """
    # Load & preprocess
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    image  = Image.open(image_path).convert("RGB")
    tensor = inference_transform(image).unsqueeze(0).to(device)  # (1,3,320,320)

    # Forward pass
    with torch.no_grad():
        logits = model(tensor)                         # (1, num_classes)
        probs  = torch.softmax(logits, dim=1)[0]      # (num_classes,)

    # Top-k
    k = min(top_k, len(class_names))
    top_probs, top_idxs = torch.topk(probs, k)

    top_k_list = [
        {
            "rank"      : i + 1,
            "class"     : class_names[idx.item()],
            "confidence": round(top_probs[i].item() * 100, 2),
        }
        for i, idx in enumerate(top_idxs)
    ]

    predicted_class = top_k_list[0]["class"]
    confidence      = top_k_list[0]["confidence"]

    # Parse "Plant___Condition"  (dataset naming convention)
    if "___" in predicted_class:
        plant, condition = predicted_class.split("___", 1)
        condition = condition.replace("_", " ")
    else:
        plant     = predicted_class
        condition = predicted_class

    is_healthy = "healthy" in condition.lower()

    return {
        "predicted_class": predicted_class,
        "confidence"      : confidence,
        "plant"           : plant,
        "condition"       : condition,
        "is_healthy"      : is_healthy,
        "top_k"           : top_k_list,
    }


def predict_from_pil(
    pil_image: Image.Image,
    model: nn.Module,
    class_names: list,
    device: str,
    top_k: int = 5,
) -> dict:
    """
    Same as predict_disease() but accepts a PIL Image directly.
    Used by app.py (FastAPI) where the image comes from an upload,
    not a file path.
    """
    tensor = inference_transform(pil_image.convert("RGB")).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs  = torch.softmax(logits, dim=1)[0]

    k = min(top_k, len(class_names))
    top_probs, top_idxs = torch.topk(probs, k)

    top_k_list = [
        {
            "rank"      : i + 1,
            "class"     : class_names[idx.item()],
            "confidence": round(top_probs[i].item() * 100, 2),
        }
        for i, idx in enumerate(top_idxs)
    ]

    predicted_class = top_k_list[0]["class"]
    confidence      = top_k_list[0]["confidence"]

    if "___" in predicted_class:
        plant, condition = predicted_class.split("___", 1)
        condition = condition.replace("_", " ")
    else:
        plant     = predicted_class
        condition = predicted_class

    is_healthy = "healthy" in condition.lower()

    return {
        "predicted_class": predicted_class,
        "confidence"      : confidence,
        "plant"           : plant,
        "condition"       : condition,
        "is_healthy"      : is_healthy,
        "top_k"           : top_k_list,
    }


# =============================================================================
# 4. CLI — standalone usage
# =============================================================================
def _print_result(result: dict):
    print(f"\n{'='*55}")
    print(f"  Plant     : {result['plant']}")
    print(f"  Condition : {result['condition']}")
    print(f"  Healthy   : {'✅ Yes' if result['is_healthy'] else '❌ No'}")
    print(f"  Top prediction: {result['predicted_class']}  ({result['confidence']:.2f}%)")
    print(f"\n  {'Rank':<5} {'Class':<40} {'Confidence':>10}")
    print(f"  {'-'*58}")
    for item in result["top_k"]:
        bar = "█" * int(item["confidence"] / 5)
        print(f"  {item['rank']:<5} {item['class']:<40} {item['confidence']:>8.2f}%  {bar}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgriGPT — Plant Disease Inference")
    parser.add_argument("--image",        type=str, required=True,
                        help="Path to leaf image (JPG/PNG)")
    parser.add_argument("--weights",      type=str, default=WEIGHTS_PATH,
                        help=f"Model weights .pth  (default: {WEIGHTS_PATH})")
    parser.add_argument("--classes",      type=str, default=CLASSES_PATH,
                        help=f"class_names.json    (default: {CLASSES_PATH})")
    parser.add_argument("--top_k",        type=int, default=5,
                        help="Number of top predictions (default: 5)")
    parser.add_argument("--device",       type=str, default=DEVICE,
                        choices=["cuda", "cpu"],
                        help=f"Device  (default: {DEVICE})")
    args = parser.parse_args()

    model, class_names, device = load_model(args.weights, args.classes, args.device)
    result = predict_disease(args.image, model, class_names, device, top_k=args.top_k)
    _print_result(result)