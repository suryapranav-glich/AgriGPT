# =============================================================================
# AgriGPT — Feature 7: Crop Price Prediction & Market Advisor (Agent 3)
# market/router.py
# =============================================================================

from __future__ import annotations

import asyncio
import json
import math
import os
import random
import zlib
from datetime import date, timedelta
from typing import Any, AsyncIterator, Literal, Optional, TypedDict

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

load_dotenv()

# ── Optional heavy deps — graceful fallback if not yet installed ──────────────

# Prophet
try:
    import pandas as pd
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False

# statsmodels ARIMA
try:
    from statsmodels.tsa.arima.model import ARIMA
    import numpy as np
    HAS_ARIMA = True
except ImportError:
    HAS_ARIMA = False

# LangChain + LangGraph (Google Gemini)
try:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import END, StateGraph
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

# Redis
try:
    import redis.asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

# Motor (async MongoDB)
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False

# ── Environment ───────────────────────────────────────────────────────────────

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
AGMARKNET_API_KEY = os.getenv("AGMARKNET_API_KEY", "")
REDIS_URL         = os.getenv("REDIS_URL", "redis://localhost:6379")
MONGODB_URI       = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

# ── Router Setup ──────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/market", tags=["Market Predictor & Advisor"])

# ── Redis client (singleton) ──────────────────────────────────────────────────

_redis: Any = None

async def get_redis():
    global _redis
    if HAS_REDIS and _redis is None:
        try:
            _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception:
            _redis = None
    return _redis

# ── MongoDB client (singleton) ────────────────────────────────────────────────

_mongo: Any = None

def get_mongo():
    global _mongo
    if HAS_MONGO and _mongo is None:
        try:
            _mongo = AsyncIOMotorClient(MONGODB_URI)
        except Exception:
            _mongo = None
    return _mongo

# ── Agmarknet / data.gov.in ───────────────────────────────────────────────────

AGMARKNET_URL = (
    "https://api.data.gov.in/resource/"
    "9ef84268-d588-465a-a308-a864a43d0070"
)

# Blueprint crop list
CROP_BASE_PRICES: dict[str, float] = {
    "Tomato":    2200, "Onion":    1800, "Paddy":     2100,
    "Cotton":    6500, "Maize":    1900, "Chilli":    8000,
    "Groundnut": 5500, "Soybean":  4200, "Sugarcane": 3500,
    "Wheat":     2300,
}

# Telangana + AP mandis from blueprint target districts
DISTRICT_MARKETS: dict[str, list[dict]] = {
    "Adilabad": [
        {"name": "Adilabad APMC", "dist_km": 5},
        {"name": "Nirmal APMC", "dist_km": 82},
        {"name": "Bhainsa APMC", "dist_km": 60},
        {"name": "Bellampally APMC", "dist_km": 98},
        {"name": "Mancherial APMC", "dist_km": 110},
    ],
    "Anantapur": [
        {"name": "Anantapur APMC", "dist_km": 4},
        {"name": "Dharmavaram APMC", "dist_km": 42},
        {"name": "Tadipatri APMC", "dist_km": 55},
        {"name": "Guntakal APMC", "dist_km": 72},
        {"name": "Hindupur APMC", "dist_km": 105},
    ],
    "Eluru": [
        {"name": "Eluru APMC", "dist_km": 4},
        {"name": "Bhimadole APMC", "dist_km": 22},
        {"name": "Chintalapudi APMC", "dist_km": 45},
        {"name": "Tadepalligudem APMC", "dist_km": 48},
        {"name": "Jangareddygudem APMC", "dist_km": 52},
    ],
    "Guntur": [
        {"name": "Guntur APMC", "dist_km": 4},
        {"name": "Mangalagiri APMC", "dist_km": 22},
        {"name": "Tenali APMC", "dist_km": 28},
        {"name": "Sattenapalle APMC", "dist_km": 32},
        {"name": "Narasaraopet APMC", "dist_km": 46},
    ],
    "Hyderabad": [
        {"name": "Bowenpally APMC", "dist_km": 5},
        {"name": "Gaddiannaram APMC", "dist_km": 14},
        {"name": "Kukatpally APMC", "dist_km": 18},
        {"name": "Shamshabad APMC", "dist_km": 29},
        {"name": "Tandur APMC", "dist_km": 72},
    ],
    "Kadapa": [
        {"name": "Kadapa APMC", "dist_km": 3},
        {"name": "Rayachoty APMC", "dist_km": 50},
        {"name": "Proddatur APMC", "dist_km": 52},
        {"name": "Rajampet APMC", "dist_km": 54},
        {"name": "Pulivendula APMC", "dist_km": 74},
    ],
    "Kakinada": [
        {"name": "Samalkot APMC", "dist_km": 12},
        {"name": "Peddapuram APMC", "dist_km": 18},
        {"name": "Mandapeta APMC", "dist_km": 42},
        {"name": "Rajahmundry APMC", "dist_km": 60},
        {"name": "Kakinada APMC", "dist_km": 3},
    ],
    "Karimnagar": [
        {"name": "Karimnagar APMC", "dist_km": 3},
        {"name": "Choppadandi APMC", "dist_km": 18},
        {"name": "Huzurabad APMC", "dist_km": 30},
        {"name": "Peddapalli APMC", "dist_km": 36},
        {"name": "Jagtial APMC", "dist_km": 48},
    ],
    "Khammam": [
        {"name": "Khammam APMC", "dist_km": 4},
        {"name": "Wyra APMC", "dist_km": 24},
        {"name": "Kothagudem APMC", "dist_km": 40},
        {"name": "Madhira APMC", "dist_km": 52},
        {"name": "Sathupally APMC", "dist_km": 76},
    ],
    "Kurnool": [
        {"name": "Kurnool APMC", "dist_km": 3},
        {"name": "Alur APMC", "dist_km": 38},
        {"name": "Dhone APMC", "dist_km": 44},
        {"name": "Nandyal APMC", "dist_km": 56},
        {"name": "Adoni APMC", "dist_km": 61},
    ],
    "Mahabubnagar": [
        {"name": "Mahabubnagar APMC", "dist_km": 3},
        {"name": "Jadcherla APMC", "dist_km": 18},
        {"name": "Nagarkurnool APMC", "dist_km": 48},
        {"name": "Wanaparthy APMC", "dist_km": 62},
        {"name": "Gadwal APMC", "dist_km": 98},
    ],
    "Medak": [
        {"name": "Medak APMC", "dist_km": 4},
        {"name": "Toopran APMC", "dist_km": 35},
        {"name": "Sangareddy APMC", "dist_km": 50},
        {"name": "Gajwel APMC", "dist_km": 52},
        {"name": "Siddipet APMC", "dist_km": 68},
    ],
    "Nalgonda": [
        {"name": "Nalgonda APMC", "dist_km": 5},
        {"name": "Nakrekal APMC", "dist_km": 28},
        {"name": "Miryalaguda APMC", "dist_km": 42},
        {"name": "Suryapet APMC", "dist_km": 45},
        {"name": "Bhongir APMC", "dist_km": 70},
    ],
    "Nellore": [
        {"name": "Nellore APMC", "dist_km": 4},
        {"name": "Gudur APMC", "dist_km": 38},
        {"name": "Kavali APMC", "dist_km": 54},
        {"name": "Naidupeta APMC", "dist_km": 58},
        {"name": "Venkatagiri APMC", "dist_km": 75},
    ],
    "Nizamabad": [
        {"name": "Nizamabad APMC", "dist_km": 4},
        {"name": "Armoor APMC", "dist_km": 28},
        {"name": "Bodhan APMC", "dist_km": 32},
        {"name": "Banswada APMC", "dist_km": 55},
        {"name": "Kamareddy APMC", "dist_km": 61},
    ],
    "Rangareddy": [
        {"name": "Rajendranagar APMC", "dist_km": 15},
        {"name": "Chevella APMC", "dist_km": 28},
        {"name": "Ibrahimpatnam APMC", "dist_km": 35},
        {"name": "Vikarabad APMC", "dist_km": 42},
        {"name": "Shadnagar APMC", "dist_km": 50},
    ],
    "Tirupati": [
        {"name": "Tirupati APMC", "dist_km": 5},
        {"name": "Srikalahasti APMC", "dist_km": 38},
        {"name": "Pileru APMC", "dist_km": 60},
        {"name": "Chittoor APMC", "dist_km": 70},
        {"name": "Madanapalle APMC", "dist_km": 115},
    ],
    "Vijayawada": [
        {"name": "Vijayawada APMC", "dist_km": 3},
        {"name": "Tenali APMC", "dist_km": 32},
        {"name": "Guntur APMC", "dist_km": 38},
        {"name": "Machilipatnam APMC", "dist_km": 61},
        {"name": "Eluru APMC", "dist_km": 75},
    ],
    "Visakhapatnam": [
        {"name": "Visakhapatnam APMC", "dist_km": 5},
        {"name": "Anakapalle APMC", "dist_km": 28},
        {"name": "Bheemunipatnam APMC", "dist_km": 32},
        {"name": "Narsipatnam APMC", "dist_km": 72},
        {"name": "Paderu APMC", "dist_km": 110},
    ],
    "Warangal": [
        {"name": "Warangal APMC", "dist_km": 4},
        {"name": "Kazipet APMC", "dist_km": 7},
        {"name": "Hanamkonda APMC", "dist_km": 9},
        {"name": "Parkal APMC", "dist_km": 33},
        {"name": "Narsampet APMC", "dist_km": 45},
    ],
    "Chittoor": [
        {"name": "Madanapalle APMC", "dist_km": 5},
        {"name": "Chittoor APMC", "dist_km": 10},
        {"name": "Punganur APMC", "dist_km": 32},
        {"name": "Kalikiri APMC", "dist_km": 40},
        {"name": "Tirupati APMC", "dist_km": 72},
    ],
    "Suryapet": [
        {"name": "Suryapet APMC", "dist_km": 3},
        {"name": "Kodad APMC", "dist_km": 42},
        {"name": "Huzurnagar APMC", "dist_km": 48},
        {"name": "Nalgonda APMC", "dist_km": 45},
        {"name": "Miryalaguda APMC", "dist_km": 60},
    ],
    "Siddipet": [
        {"name": "Siddipet APMC", "dist_km": 3},
        {"name": "Gajwel APMC", "dist_km": 28},
        {"name": "Dubbak APMC", "dist_km": 30},
        {"name": "Husnabad APMC", "dist_km": 42},
        {"name": "Medak APMC", "dist_km": 68},
    ],
    "West Godavari": [
        {"name": "Tadepalligudem APMC", "dist_km": 4},
        {"name": "Bhimavaram APMC", "dist_km": 35},
        {"name": "Tanuku APMC", "dist_km": 25},
        {"name": "Palakollu APMC", "dist_km": 48},
        {"name": "Eluru APMC", "dist_km": 48},
    ],
    "Vizianagaram": [
        {"name": "Vizianagaram APMC", "dist_km": 4},
        {"name": "Cheepurupalli APMC", "dist_km": 32},
        {"name": "Parvathipuram APMC", "dist_km": 80},
        {"name": "Bobbil APMC", "dist_km": 55},
        {"name": "Visakhapatnam APMC", "dist_km": 60},
    ],
    "Sangareddy": [
        {"name": "Sangareddy APMC", "dist_km": 3},
        {"name": "Sadasivpet APMC", "dist_km": 18},
        {"name": "Jogipet APMC", "dist_km": 36},
        {"name": "Zaheerabad APMC", "dist_km": 50},
        {"name": "Kondan APMC", "dist_km": 45},
    ],
}

# ── Price simulation (Agmarknet fallback) ─────────────────────────────────────

def simulate_price_history(crop: str, district: str, days: int = 90) -> list[dict]:
    """
    Realistic price simulation using seasonal sine wave + uptrend + Gaussian noise.
    Used when AGMARKNET_API_KEY is not set or API is unreachable.
    Takes district into account to ensure prices are distinct per district.
    """
    base  = CROP_BASE_PRICES.get(crop, 2000)
    
    # Deterministic price level multiplier per district (approx 0.82 to 1.18)
    dist_seed = zlib.adler32(district.encode("utf-8"))
    dist_rng = random.Random(dist_seed)
    dist_mult = dist_rng.uniform(0.82, 1.18)
    base = base * dist_mult
    
    today = date.today()
    # Seed noise generation using both crop and district so trend-noise is distinct
    combined_seed = zlib.adler32(f"{crop}:{district}".encode("utf-8"))
    rng   = random.Random(combined_seed)
    result = []
    for i in range(days):
        d        = today - timedelta(days=days - 1 - i)
        seasonal = math.sin(i / 12.0) * base * 0.09
        trend    = (i / days) * base * 0.14
        noise    = rng.gauss(0, base * 0.022)
        price    = max(round(base + seasonal + trend + noise, 2), base * 0.4)
        result.append({"date": d.isoformat(), "price": price})
    return result


async def fetch_agmarknet(crop: str, district: str) -> list[dict] | None:
    """Fetch real mandi prices from data.gov.in Agmarknet dataset."""
    if not AGMARKNET_API_KEY:
        return None
    cache_key = f"agmarknet:{crop}:{district}"
    r = await get_redis()
    if r:
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    try:
        params = {
            "api-key":            AGMARKNET_API_KEY,
            "format":             "json",
            "filters[commodity]": crop,
            "filters[district]":  district,
            "limit":              365,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(AGMARKNET_URL, params=params)
            resp.raise_for_status()
            records = resp.json().get("records", [])
        prices = [
            {"date": rec["arrival_date"], "price": float(rec["modal_price"])}
            for rec in records
            if rec.get("modal_price")
        ]
        if prices:
            prices.sort(key=lambda x: x["date"])
            # Cache for 6 hours (Blueprint: Redis to reduce API costs)
            if r:
                await r.setex(cache_key, 21600, json.dumps(prices))
            return prices
    except Exception:
        pass
    return None

# ── Forecasting: Prophet (primary) / ARIMA (fallback) ────────────────────────

def run_prophet_forecast(history: list[dict], horizon: int = 30) -> list[dict]:
    """
    Meta Prophet — handles weekly seasonality + trend changepoints.
    Blueprint specifies Prophet for short-term price forecasting.
    """
    df       = pd.DataFrame(history)
    df.columns = ["ds", "y"]
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"]  = pd.to_numeric(df["y"], errors="coerce").ffill()

    m = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=len(history) >= 180,
        changepoint_prior_scale=0.05,
        interval_width=0.80,
        seasonality_mode="multiplicative",
    )
    m.fit(df)
    future   = m.make_future_dataframe(periods=horizon)
    forecast = m.predict(future)

    return [
        {
            "date":  str(row["ds"].date()),
            "price": round(float(row["yhat"]),       2),
            "lower": round(float(row["yhat_lower"]), 2),
            "upper": round(float(row["yhat_upper"]), 2),
        }
        for _, row in forecast.tail(horizon).iterrows()
    ]


def run_arima_forecast(history: list[dict], horizon: int = 30) -> list[dict]:
    """
    ARIMA(2,1,2) via statsmodels — blueprint-specified fallback model.
    Falls back to exponential smoothing if statsmodels is unavailable.
    """
    prices    = [h["price"] for h in history]
    last_date = date.fromisoformat(history[-1]["date"])

    if HAS_ARIMA and len(prices) >= 30:
        try:
            model = ARIMA(prices, order=(2, 1, 2))
            fit   = model.fit()
            pred  = fit.forecast(steps=horizon)
            conf  = fit.get_forecast(steps=horizon).conf_int(alpha=0.20)
            return [
                {
                    "date":  (last_date + timedelta(days=i + 1)).isoformat(),
                    "price": round(float(pred.iloc[i]), 2),
                    "lower": round(float(conf.iloc[i, 0]), 2),
                    "upper": round(float(conf.iloc[i, 1]), 2),
                }
                for i in range(horizon)
            ]
        except Exception:
            pass

    # ── Exponential smoothing fallback (zero extra deps) ──────────────────────
    alpha    = 0.3
    s        = prices[0]
    smoothed = [s]
    for p in prices[1:]:
        s = alpha * p + (1 - alpha) * s
        smoothed.append(s)

    level = smoothed[-1]
    # Calculate trend from last 14 days (or available)
    lookback = min(14, len(prices) - 1)
    trend    = (prices[-1] - prices[-(lookback + 1)]) / lookback if lookback > 0 else 0

    # Weekly seasonal deltas (capped to ±15% of level to avoid runaway noise)
    season = []
    for i in range(7):
        idx   = -(7 - i)
        delta = (prices[idx] - smoothed[idx]) if abs(idx) <= len(prices) else 0
        season.append(max(min(delta, level * 0.15), -level * 0.15))

    rng    = random.Random(42)
    result = []
    for i in range(1, horizon + 1):
        level += trend * (0.92 ** i)
        pred   = level + season[i % 7] + rng.gauss(0, abs(level) * 0.012)
        pred   = max(pred, 100)
        result.append({
            "date":  (last_date + timedelta(days=i)).isoformat(),
            "price": round(pred, 2),
            "lower": round(pred * 0.91, 2),
            "upper": round(pred * 1.09, 2),
        })
    return result


def get_forecast(history: list[dict], horizon: int = 30) -> list[dict]:
    if HAS_PROPHET:
        try:
            return run_prophet_forecast(history, horizon)
        except Exception:
            pass
    return run_arima_forecast(history, horizon)

# ── Sell / Wait / Hold logic ──────────────────────────────────────────────────

def compute_recommendation(
    current:  float,
    forecast: list[dict],
    history:  list[dict],
) -> dict:
    hist_prices = [h["price"] for h in history[-90:]]
    avg_90d     = sum(hist_prices) / len(hist_prices) if hist_prices else current
    max_90d     = max(hist_prices)                     if hist_prices else current

    fcast_7d   = [f["price"] for f in forecast[:7]]
    fcast_avg  = sum(fcast_7d) / len(fcast_7d) if fcast_7d else current
    fcast_peak = max(fcast_7d)                 if fcast_7d else current

    pct_vs_avg   = round(((current - avg_90d) / avg_90d) * 100, 1)
    pct_vs_peak  = round(((current - max_90d) / max_90d) * 100, 1)
    trend_7d     = round(((fcast_avg - current) / current) * 100, 1)
    days_to_peak = next(
        (i + 1 for i, f in enumerate(forecast[:14]) if f["price"] >= fcast_peak),
        7,
    )

    if trend_7d >= 4 and pct_vs_peak < -8:
        action     = "WAIT"
        reason     = (
            f"Prices forecast to rise {trend_7d:+.1f}% over next 7 days. "
            f"Current price is {abs(pct_vs_peak):.0f}% below the 90-day peak. "
            f"Peak expected in ~{days_to_peak} days — hold for better returns."
        )
        confidence = min(92, 58 + abs(trend_7d) * 4)
    elif trend_7d <= -3 or pct_vs_peak >= -4:
        action     = "SELL"
        reason     = (
            f"Price is near the 90-day peak (within {abs(pct_vs_peak):.0f}%). "
            f"Forecast shows {abs(trend_7d):.1f}% decline over 7 days. "
            "Sell now to lock in gains before prices fall further."
        )
        confidence = min(92, 58 + abs(trend_7d) * 4)
    else:
        action     = "HOLD"
        reason     = (
            "Market is stable with no strong directional signal. "
            f"Price is {pct_vs_avg:+.1f}% vs 90-day average. "
            "Monitor for 2–3 days before deciding."
        )
        confidence = 55

    return {
        "action":          action,
        "reason":          reason,
        "confidence":      round(confidence),
        "pct_vs_90d_avg":  pct_vs_avg,
        "pct_vs_90d_peak": pct_vs_peak,
        "forecast_7d":     trend_7d,
        "days_to_peak":    days_to_peak,
    }

# ── Nearby markets ────────────────────────────────────────────────────────────

def build_nearby_markets(crop: str, district: str, base: float) -> list[dict]:
    markets = DISTRICT_MARKETS.get(district, DISTRICT_MARKETS["Hyderabad"])
    combined_str = f"{crop}:{district}:{date.today().isoformat()}"
    market_seed = zlib.adler32(combined_str.encode("utf-8"))
    rng     = random.Random(market_seed)
    result  = []
    for m in markets:
        var   = rng.uniform(-0.07, 0.07)
        price = round(base * (1 + var))
        result.append({
            "name":         m["name"],
            "dist_km":      m["dist_km"],
            "price":        price,
            "trend":        "up" if var >= 0 else "down",
            "arrivals_qtl": rng.randint(40, 900),
        })
    return sorted(result, key=lambda x: -x["price"])

# ── LangChain / LangGraph — Market Agent (Agent 3) ───────────────────────────

# LangGraph state definition (TypedDict for proper typing)
class MarketAgentState(TypedDict):
    crop:        str
    district:    str
    price:       float
    action:      str
    trend_7d:    float
    pct_avg:     float
    advisory:    str


def get_llm():
    """
    Blueprint: Google Gemini 1.5 Flash via LangChain Google GenAI integration.
    Fast + cost-efficient, ideal for streaming advisory responses.
    """
    if GEMINI_API_KEY and HAS_LANGCHAIN:
        return ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY,
            model="gemini-2.5-flash",
            temperature=0.3,
            streaming=True,
        )
    return None


# ── IMPORTANT: LangChain ChatPromptTemplate does NOT support Python format
# specs like {var:.1f} inside template strings. All numeric formatting must
# be done BEFORE passing values into the chain. ─────────────────────────────

MARKET_SYSTEM_PROMPT = """You are AgriGPT's Expert Market Advisor (Agent 3) specialising in \
Telangana and Andhra Pradesh agriculture. You advise smallholder farmers in warm, \
practical, and actionable language.

Instead of just repeating the input percentages and numbers (which are already on the dashboard), \
provide valuable, context-rich advice. For example:
- If recommending to HOLD or WAIT: Explain practical storage tips (e.g., keeping tomatoes in ventilated crates, avoiding direct sunlight, managing moisture for grains/onions to prevent fungal growth/sprouting) and check local weather conditions (like incoming rains) that could disrupt transport or damage harvest.
- If recommending to SELL: Suggest targeting specific high-performing nearby APMC mandis, planning harvesting time to avoid midday heat, or advising on quick transportation to minimize post-harvest losses.
- Keep the advisory to 3-5 sentences.
- Always write the entire advisory in {language_name}. Translate all terms (crop names, districts, etc.) into the native script of {language_name}.
- Avoid dry academic jargon. Speak like a friendly local agricultural officer who understands the region's conditions."""

MARKET_HUMAN_PROMPT = """Crop: {crop}
District: {district}
Current mandi price: {price_str} rupees per quintal
Recommendation: {action}
7-day price forecast trend: {trend_7d_str}
Current price vs 90-day average: {pct_avg_str}

Write a 3-5 sentence market advisory for this farmer in {language_name}."""


def _build_market_chain():
    """Build the LangChain prompt → Gemini → parser chain."""
    llm   = get_llm()
    if not llm:
        return None
    prompt = ChatPromptTemplate.from_messages([
        ("system", MARKET_SYSTEM_PROMPT),
        ("human",  MARKET_HUMAN_PROMPT),
    ])
    return prompt | llm | StrOutputParser()


# ── LangGraph Agent 3 node ────────────────────────────────────────────────────

def _build_market_graph():
    """
    Minimal LangGraph single-node graph for Agent 3.
    Blueprint: LangGraph for multi-agent orchestration.
    In the full system this node is wired into the supervisor graph.
    """
    if not HAS_LANGCHAIN:
        return None

    async def market_advisory_node(state: MarketAgentState) -> MarketAgentState:
        chain = _build_market_chain()
        if not chain:
            state["advisory"] = "Advisory unavailable — configure GEMINI_API_KEY."
            return state
        result = await chain.ainvoke({
            "crop":       state["crop"],
            "district":  state["district"],
            "price_str": f"Rs {state['price']:,.0f}",
            "action":    state["action"],
            "trend_7d_str": f"{state['trend_7d']:+.1f}%",
            "pct_avg_str":  f"{state['pct_avg']:+.1f}%",
            "language_name": "English",
        })
        state["advisory"] = result
        return state

    graph = StateGraph(MarketAgentState)
    graph.add_node("market_advisor", market_advisory_node)
    graph.set_entry_point("market_advisor")
    graph.add_edge("market_advisor", END)
    return graph.compile()


# Build graph once at startup
_market_graph = None

def load_market_graph():
    """Initialize the LangGraph instance for the market advisor."""
    global _market_graph
    _market_graph = _build_market_graph()


async def run_market_agent_stream(
    crop:     str,
    district: str,
    price:    float,
    action:   str,
    trend_7d: float,
    pct_avg:  float,
    lang:     str = "en",
) -> AsyncIterator[str]:
    """
    LangChain streaming chain: PromptTemplate → Gemini 2.5 Flash → StrOutputParser.
    Token-by-token streaming via chain.astream().
    """
    chain = _build_market_chain()

    # Determine native action representation for local fallback
    action_te = "అమ్మకం" if action == "SELL" else "వేచి ఉండడం" if action == "WAIT" else "నిల్వ ఉంచడం"
    action_hi = "बेचने" if action == "SELL" else "प्रतीक्षा करने" if action == "WAIT" else "स्टॉक रोकने"

    fallback_en = (
        f"Current {crop} price in {district} is Rs {price:,.0f} per quintal, "
        f"which is {pct_avg:+.1f}% versus the 90-day average. "
        f"The 7-day forecast shows a {trend_7d:+.1f}% movement — "
        f"the recommendation is to {action.lower()} based on this trend. "
        "Check arrivals and competing supply at your nearest APMC before deciding."
    )
    fallback_te = (
        f"{district} లో {crop} ప్రస్తుత మండి ధర క్వింటాల్‌కు రూ. {price:,.0f}, "
        f"ఇది 90 రోజుల సగటుతో పోలిస్తే {pct_avg:+.1f}%. 7 రోజుల అంచనా ప్రకారం {trend_7d:+.1f}% మార్పు ఉంటుంది — "
        f"ఈ ధోరణి ఆధారంగా మీ పంటను {action_te} చేయాలని మేము సిఫార్సు చేస్తున్నాము. "
        "నిర్ణయం తీసుకునే ముందు సమీప APMCలో వాల్యూమ్స్ మరియు పోటీ సరఫరాను తనిఖీ చేయండి."
    )
    fallback_hi = (
        f"{district} में {crop} की वर्तमान मंडी कीमत ₹{price:,.0f} प्रति क्विंटल है, "
        f"जो 90 दिनों के औसत की तुलना में {pct_avg:+.1f}% है। 7-दिन का पूर्वानुमान {trend_7d:+.1f}% बदलाव दर्शाता है — "
        f"इस प्रवृत्ति के आधार पर हम आपको {action_hi} की सलाह देते हैं। "
        "निर्णय लेने से पहले अपने नजदीकी एपीएमसी में आवक और प्रतिस्पर्धी आपूर्ति की जांच करें।"
    )

    fallback_dict = {
        "en": fallback_en,
        "te": fallback_te,
        "hi": fallback_hi,
    }
    advice = fallback_dict.get(lang, fallback_en)

    if not chain:
        for word in advice.split(" "):
            yield word + " "
            await asyncio.sleep(0.025)
        return

    lang_map = {
        "te": "Telugu",
        "hi": "Hindi",
        "en": "English",
    }
    language_name = lang_map.get(lang, "English")

    inputs = {
        "crop":        crop,
        "district":    district,
        "price_str":   f"Rs {price:,.0f}",
        "action":      action,
        "trend_7d_str": f"{trend_7d:+.1f}%",
        "pct_avg_str":  f"{pct_avg:+.1f}%",
        "language_name": language_name,
    }

    try:
        async for chunk in chain.astream(inputs):
            yield chunk
    except Exception as e:
        print(f"[Market Advisor] LangChain streaming failed: {e}. Using local heuristic advisor fallback.")
        for word in advice.split(" "):
            yield word + " "
            await asyncio.sleep(0.03)

# ── API routes ────────────────────────────────────────────────────────────────

@router.get("/prices")
async def market_prices(
    crop:       str = Query("Tomato"),
    district:   str = Query("Hyderabad"),
    range_days: int = Query(30, alias="range"),
):
    """
    Main data endpoint — returns history, forecast, recommendation, nearby markets.
    Caches Agmarknet responses in Redis for 6 hours (blueprint improvement).
    Saves query to MongoDB farm memory for authenticated users (blueprint feature).
    """
    # 1. Fetch price history
    history = await fetch_agmarknet(crop, district)
    if not history:
        history = simulate_price_history(crop, district, days=90)

    displayed = history[-range_days:]

    # 2. Forecast
    forecast = get_forecast(history, horizon=30)

    # 3. Current stats
    current    = history[-1]["price"]
    price_7ago = history[-8]["price"] if len(history) >= 8 else current
    change_7d  = round(current - price_7ago, 2)
    change_pct = round((change_7d / price_7ago) * 100, 1) if price_7ago else 0

    # 4. Recommendation
    rec = compute_recommendation(current, forecast, history)

    # 5. Nearby markets
    markets = build_nearby_markets(crop, district, current)

    # 6. Save to MongoDB farm memory (blueprint: per-user crop history)
    mongo = get_mongo()
    if mongo:
        try:
            db  = mongo["agrigpt"]
            col = db["market_queries"]
            await col.insert_one({
                "crop":      crop,
                "district":  district,
                "price":     current,
                "action":    rec["action"],
                "timestamp": date.today().isoformat(),
            })
        except Exception:
            pass

    return {
        "crop":           crop,
        "district":       district,
        "current_price":  current,
        "change_7d":      change_7d,
        "change_7d_pct":  change_pct,
        "history":        displayed,
        "forecast":       forecast,
        "recommendation": rec,
        "nearby_markets": markets,
        "forecast_model": "prophet" if HAS_PROPHET else "arima",
        "data_source":    "agmarknet" if AGMARKNET_API_KEY else "simulation",
    }


@router.get("/advisor/stream")
async def advisor_stream(
    crop:     str   = Query("Tomato"),
    district: str   = Query("Hyderabad"),
    price:    float = Query(2200),
    action:   str   = Query("SELL"),
    trend_7d: float = Query(2.5),
    pct_avg:  float = Query(8.3),
    lang:     str   = Query("en"),
):
    """
    SSE streaming endpoint — LangChain chain streams Gemini tokens one-by-one.
    Blueprint: FastAPI StreamingResponse + LangChain .astream() for non-blocking advisory.
    LLM: Google Gemini 1.5 Flash via langchain-google-genai (NOT OpenAI / Grok).
    """
    async def generate():
        async for token in run_market_agent_stream(
            crop, district, price, action, trend_7d, pct_avg, lang
        ):
            yield f"data: {json.dumps({'text': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/crops")
async def list_crops():
    return {"crops": sorted(CROP_BASE_PRICES.keys())}


@router.get("/districts")
async def list_districts():
    return {"districts": sorted(DISTRICT_MARKETS.keys())}


@router.get("/health")
async def health():
    r = await get_redis()
    return {
        "status":      "ok",
        "llm":         "gemini-1.5-flash",
        "llm_ready":   bool(GEMINI_API_KEY and HAS_LANGCHAIN),
        "prophet":     HAS_PROPHET,
        "arima":       HAS_ARIMA,
        "redis":       r is not None,
        "mongodb":     get_mongo() is not None,
        "agmarknet":   bool(AGMARKNET_API_KEY),
        "data_source": "agmarknet" if AGMARKNET_API_KEY else "simulation",
        "langchain":   HAS_LANGCHAIN,
    }
