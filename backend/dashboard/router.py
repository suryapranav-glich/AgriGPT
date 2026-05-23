# =============================================================================
# backend/dashboard/router.py — Dashboard metrics endpoint
#
# Routes:
#   GET  /dashboard/metrics       → per-user dashboard data from MongoDB
#   PATCH /dashboard/metrics      → update user's crop/mandi/irrigation data
#   POST /dashboard/activity      → log a new activity event for the user
# =============================================================================

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from auth.db import (
    users_col,
    farm_profiles_col,
    chat_history_col,
    disease_diagnoses_col,
    irrigation_logs_col,
    market_queries_col,
    voice_queries_col,
)
from auth.utils import decode_token

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# =============================================================================
# ── Core Helper: always query with BOTH ObjectId and str forms of user_id ──
# This fixes the root cause — documents saved by different agents use
# different types (some save ObjectId, some save str). We query both always.
# =============================================================================
def _build_user_filter(uid) -> dict:
    """
    Returns a MongoDB filter that matches user_id stored as either
    ObjectId OR string. Handles both forms transparently.
    """
    if isinstance(uid, ObjectId):
        return {"user_id": {"$in": [uid, str(uid)]}}
    # uid is already a str
    try:
        return {"user_id": {"$in": [ObjectId(uid), uid]}}
    except Exception:
        return {"user_id": uid}


def _require_user_id(authorization: str) -> ObjectId:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.split(" ", 1)[1]
    uid = decode_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        return ObjectId(uid)
    except Exception:
        return uid


# ── Models ────────────────────────────────────────────────────────────────────
class MetricsUpdate(BaseModel):
    active_crop: Optional[str] = None
    last_diagnosis: Optional[str] = None
    last_diagnosis_severity: Optional[str] = None
    next_irrigation: Optional[str] = None
    mandi_price: Optional[float] = None
    mandi_price_change: Optional[float] = None
    mandi_location: Optional[str] = None


class ActivityEvent(BaseModel):
    agent: str       # "disease" | "market" | "weather" | "scheme" | "soil" | "fertilizer"
    query: str       # Short description of what was asked/done
    status: str      # "resolved" | "answered" | "pending"


# =============================================================================
# GET /dashboard/metrics
# =============================================================================
@router.get("/metrics")
def get_metrics(authorization: str = Header(default="")):
    uid = _require_user_id(authorization)

    # ── 1. Fetch user doc ─────────────────────────────────────────────────────
    doc = users_col().find_one({"_id": uid})
    if not doc:
        # Try string form as fallback
        doc = users_col().find_one({"_id": str(uid)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_filter = _build_user_filter(uid)

    # ── 2. Farm profile (manual overrides / fallback values) ──────────────────
    farm = farm_profiles_col().find_one(user_filter) or {}

    # ── 3. Active Crop — from latest market query ─────────────────────────────
    latest_market = market_queries_col().find_one(
        user_filter, sort=[("timestamp", -1)]
    )
    if latest_market:
        active_crop     = latest_market.get("crop") or farm.get("active_crop") or "Not specified"
        mandi_price     = latest_market.get("price") or farm.get("mandi_price")
        mandi_location  = latest_market.get("district") or farm.get("mandi_location", "Local Market")
    else:
        active_crop     = farm.get("active_crop") or "Not specified"
        mandi_price     = farm.get("mandi_price")
        mandi_location  = farm.get("mandi_location", "Local Market")

    # Mandi price % change: compare latest two market queries for same crop
    mandi_price_change = farm.get("mandi_price_change", 0.0)
    if latest_market and active_crop:
        prev_market = market_queries_col().find_one(
            {**user_filter, "crop": active_crop,
             "_id": {"$ne": latest_market["_id"]}},
            sort=[("timestamp", -1)]
        )
        if prev_market and prev_market.get("price") and latest_market.get("price"):
            prev_p    = float(prev_market["price"])
            latest_p  = float(latest_market["price"])
            if prev_p > 0:
                mandi_price_change = round(((latest_p - prev_p) / prev_p) * 100, 1)

    # ── 4. Disease Diagnosis — latest diagnosis record ────────────────────────
    latest_disease = disease_diagnoses_col().find_one(
        user_filter, sort=[("updated_at", -1)]
    )
    # Also try created_at if updated_at not present
    if not latest_disease:
        latest_disease = disease_diagnoses_col().find_one(
            user_filter, sort=[("created_at", -1)]
        )

    if latest_disease:
        last_diagnosis          = (
            latest_disease.get("disease_detected")
            or latest_disease.get("disease")
            or latest_disease.get("result")
            or farm.get("last_diagnosis")
            or "No diagnosis yet"
        )
        last_diagnosis_severity = (
            latest_disease.get("severity")
            or farm.get("last_diagnosis_severity", "none")
        )
    else:
        last_diagnosis          = farm.get("last_diagnosis") or "No diagnosis yet"
        last_diagnosis_severity = farm.get("last_diagnosis_severity", "none")

    # ── 5. Irrigation — latest schedule ───────────────────────────────────────
    latest_irrigation = irrigation_logs_col().find_one(
        user_filter, sort=[("timestamp", -1)]
    )
    if not latest_irrigation:
        latest_irrigation = irrigation_logs_col().find_one(
            user_filter, sort=[("created_at", -1)]
        )

    if latest_irrigation:
        next_irrigation = (
            latest_irrigation.get("next_schedule")
            or latest_irrigation.get("next_irrigation")
            or latest_irrigation.get("schedule")
            or farm.get("next_irrigation")
            or "Not scheduled"
        )
    else:
        next_irrigation = farm.get("next_irrigation") or "Not scheduled"

    # ── 6. Recent Activity feed ───────────────────────────────────────────────
    # Pull from chat_history (all agents log here)
    raw_chat = list(
        chat_history_col()
        .find(user_filter)
        .sort("created_at", -1)
        .limit(10)
    )

    # Pull from voice_queries
    raw_voice = list(
        voice_queries_col()
        .find(user_filter)
        .sort("timestamp", -1)
        .limit(5)
    )

    combined_activity = []

    for c in raw_chat:
        dt = c.get("created_at")
        if dt:
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except Exception:
                    dt = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)

        query_text = (
            c.get("query")
            or c.get("message")
            or c.get("content")
            or ""
        )
        if not query_text:
            continue  # skip empty entries

        combined_activity.append({
            "agent":   c.get("agent", "general"),
            "query":   query_text,
            "status":  c.get("status", "answered"),
            "time_dt": dt,
            "time":    _relative_time(dt),
        })

    for v in raw_voice:
        ts_str = v.get("timestamp", "")
        dt = None
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.now(timezone.utc)
        if not dt:
            dt = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        transcript = v.get("transcript") or v.get("query") or ""
        if not transcript:
            continue

        combined_activity.append({
            "agent":   v.get("agent_type", "market"),
            "query":   transcript,
            "status":  "answered",
            "time_dt": dt,
            "time":    _relative_time(dt),
        })

    # Sort by most recent first, deduplicate by query text
    combined_activity.sort(
        key=lambda x: x["time_dt"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    # Deduplicate — keep first occurrence of each (agent, query) pair
    seen = set()
    deduped = []
    for item in combined_activity:
        key = (item["agent"], item["query"][:60])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    activity = [
        {
            "agent":  x["agent"],
            "query":  x["query"],
            "status": x["status"],
            "time":   x["time"],
        }
        for x in deduped[:5]
    ]

    # ── 7. Return assembled metrics ───────────────────────────────────────────
    return {
        "active_crop":             active_crop,
        "last_diagnosis":          last_diagnosis,
        "last_diagnosis_severity": last_diagnosis_severity,
        "next_irrigation":         next_irrigation,
        "mandi_price":             mandi_price,
        "mandi_price_change":      mandi_price_change,
        "mandi_location":          mandi_location,
        "location":                farm.get("state") or doc.get("location", "India"),
        "name":                    doc.get("name", "Farmer"),
        "recent_activity":         activity,
    }


# =============================================================================
# PATCH /dashboard/metrics  — manually override farm data
# =============================================================================
@router.patch("/metrics")
def update_metrics(body: MetricsUpdate, authorization: str = Header(default="")):
    uid = _require_user_id(authorization)
    user_filter = _build_user_filter(uid)

    update_fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields["updated_at"] = datetime.now(timezone.utc)
    farm_profiles_col().update_one(user_filter, {"$set": update_fields}, upsert=True)
    return {"message": "Dashboard metrics updated"}


# =============================================================================
# POST /dashboard/activity  — log a feature usage event
# =============================================================================
@router.post("/activity")
def log_activity(body: ActivityEvent, authorization: str = Header(default="")):
    uid = _require_user_id(authorization)
    doc = {
        "user_id":        uid,           # store as ObjectId consistently
        "agent":          body.agent,
        "query":          body.query,
        "status":         body.status,
        "query_language": "en",
        "created_at":     datetime.now(timezone.utc),
    }
    chat_history_col().insert_one(doc)
    return {"message": "Activity logged"}


# ── Utility ───────────────────────────────────────────────────────────────────
def _relative_time(dt: Optional[datetime]) -> str:
    if not dt:
        return "Recently"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff    = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        m = int(seconds // 60)
        return f"{m}m ago"
    if seconds < 86400:
        h = int(seconds // 3600)
        return f"{h}h ago"
    d = int(seconds // 86400)
    return f"{d}d ago"