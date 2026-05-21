import math
import httpx
import urllib.parse
from fastapi import APIRouter, HTTPException, Header
import os
from pydantic import BaseModel

from auth.db import irrigation_logs_col
from auth.utils import decode_token
from bson import ObjectId
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/irrigation", tags=["Irrigation Planner"])

class IrrigationRequest(BaseModel):
    location: str
    crop: str
    growth_stage: str
    field_size: float

# Crop coefficients (Kc) mapping based on crop and growth stage
KC_MAP = {
    "Tomato": {
        "Seedling": 0.6,
        "Vegetative": 0.8,
        "Flowering": 1.15,
        "Maturity": 0.8
    },
    "Onion": {
        "Seedling": 0.5,
        "Vegetative": 0.7,
        "Bulb Development": 1.05,
        "Maturity": 0.75
    },
    "Paddy": {
        "Seedling": 1.05,
        "Vegetative": 1.2,
        "Flowering": 1.2,
        "Maturity": 0.9
    },
    "Cotton": {
        "Seedling": 0.35,
        "Vegetative": 0.75,
        "Boll Development": 1.15,
        "Maturity": 0.6
    }
}

async def geocode_location(loc: str):
    clean_name = loc.split(",")[0].strip()
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_name)}&count=1&language=en&format=json"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()
        if not data.get("results"):
            if clean_name.lower().endswith("y"):
                alt_name = clean_name[:-1] + "i"
                url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(alt_name)}&count=1&language=en&format=json"
                res = await client.get(url)
                data = res.json()
        if data.get("results"):
            return data["results"][0]["latitude"], data["results"][0]["longitude"], f"{data['results'][0]['name']}, {data['results'][0].get('admin1', data['results'][0].get('country'))}"
    return 13.13768, 78.12999, loc # Kolar fallback

@router.post("/plan")
async def get_irrigation_plan(req: IrrigationRequest, authorization: str = Header(default="")):
    lat, lon, matched_name = await geocode_location(req.location)
    
    # Fetch 16-day daily forecast and 2-day hourly forecast for watering time
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&hourly=temperature_2m,relative_humidity_2m&timezone=auto&forecast_days=16"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    if "daily" not in data or "hourly" not in data:
        raise HTTPException(status_code=500, detail="Weather API failed")

    daily = data["daily"]
    hourly = data["hourly"]
    
    days = []
    # 15 days as requested
    for i in range(15): 
        d_raw = daily["time"][i]
        days.append({
            "date": d_raw,
            "rain_prob": daily["precipitation_probability_max"][i] if daily.get("precipitation_probability_max") else 0,
            "t_max": round(daily["temperature_2m_max"][i]),
            "t_min": round(daily["temperature_2m_min"][i])
        })

    # Today's reference ET
    t_max = days[0]["t_max"]
    t_min = days[0]["t_min"]
    ref_et = round((0.12 * t_max + 0.1 * (t_max - t_min) - 0.5) * 10) / 10

    # Determine Kc
    crop_stages = KC_MAP.get(req.crop, {})
    kc = crop_stages.get(req.growth_stage, 1.0)
    
    crop_et = ref_et * kc
    
    # Effective rain tomorrow
    tomorrow_rain_prob = days[1]["rain_prob"]
    effective_rain = round(tomorrow_rain_prob * 0.15 * 10) / 10 if tomorrow_rain_prob > 50 else 0.0
    
    net_irrigation = max(0.0, crop_et - effective_rain)
    total_water_litres = round(net_irrigation * req.field_size * 4046.86)
    
    has_heatwave = t_max >= 38 or ref_et > 6.2
    
    # Calculate best watering time
    morning_temps = hourly["temperature_2m"][5:9]
    evening_temps = hourly["temperature_2m"][17:21]
    
    best_time_window = "06:00 AM - 08:00 AM (Early Morning)"
    if morning_temps and evening_temps and min(evening_temps) < min(morning_temps):
        best_time_window = "05:00 PM - 07:00 PM (Late Evening)"

    # Save to MongoDB
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        user_id = decode_token(token)

    if user_id:
        try:
            now = datetime.now(timezone.utc)
            # "Tomorrow" if morning, or specify next day
            next_schedule = f"Tomorrow, {best_time_window}"
            
            irrigation_logs_col().insert_one({
                "user_id": ObjectId(user_id),
                "timestamp": now.isoformat(),
                "crop": req.crop,
                "location": matched_name,
                "net_irrigation": round(net_irrigation, 1),
                "next_schedule": next_schedule
            })
            
            from auth.db import chat_history_col
            chat_history_col().insert_one({
                "user_id": ObjectId(user_id),
                "agent": "weather",
                "query": f"Generated irrigation plan for {req.crop}",
                "created_at": now
            })
        except Exception as e:
            print("Failed to save irrigation log:", e)

    return {
        "location": matched_name,
        "ref_et": ref_et,
        "kc": kc,
        "crop_et": round(crop_et, 2),
        "effective_rain": effective_rain,
        "net_irrigation": round(net_irrigation, 1),
        "total_water_litres": total_water_litres,
        "has_heatwave": has_heatwave,
        "best_watering_time": best_time_window,
        "forecast_15_days": days
    }
