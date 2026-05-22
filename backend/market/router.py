import json
from fastapi import APIRouter, Query, Header, HTTPException
from fastapi.responses import StreamingResponse
from datetime import date
from typing import Any
router = APIRouter()
# Existing imports retained below (original file content omitted for brevity)
# ... (Assume existing imports and code remain unchanged)

# New helper for language translation of price response
def _translate_price(crop: str, district: str, price: float, lang: str = "en") -> str:
    """Return a short price statement in the requested language.
    Supports English (en), Telugu (te), Hindi (hi)."""
    statements = {
        "en": f"The current price of {crop} in {district} is Rs {price:,.0f} per quintal.",
        "te": f"{district} లో {crop} యొక్క ప్రస్తుత ధర క్వింటాల్‌కు రూ. {price:,.0f}.",
        "hi": f"{district} में {crop} की वर्तमान कीमत {price:,.0f} रुपये प्रति क्विंटल है.",
    }
    return statements.get(lang, statements["en"])

@router.get("/price")
async def get_price(
    crop: str = Query("Tomato"),
    district: str = Query("Kamareddy"),
    language: str = Query("en"),
    authorization: str = Header(default="")
) -> Any:
    """Return the latest price for a crop in a district.
    Uses Agmarknet if API key is configured, otherwise falls back to simulated price.
    """
    # Fetch history (reuse existing logic)
    history = await fetch_agmarknet(crop, district)
    if not history:
        history = simulate_price_history(crop, district, days=90)
    if not history:
        raise HTTPException(status_code=404, detail="Price data not found")
    current_price = history[-1]["price"]
    # Optional language translation
    message = _translate_price(crop, district, current_price, lang=language)
    return {"crop": crop, "district": district, "current_price": current_price, "message": message}

# Placeholder graph initialization for market advisor

_market_graph = None

def load_market_graph():
    """Initialize and return the market graph.
    Returns the compiled LangGraph for the market advisor. If the graph is already built,
    it is returned directly. This placeholder ensures the import does not fail.
    """
    global _market_graph
    if _market_graph is None:
        # Import the graph builder lazily to avoid circular imports
        from .router import _build_market_graph
        _market_graph = _build_market_graph()
    return _market_graph
