# =============================================================================
# backend/auth/router.py — All authentication endpoints
#
# Routes:
#   GET  /auth/config            → returns public Google client ID (safe)
#   POST /auth/signup            → email/password registration
#   POST /auth/signin            → email/password login
#   POST /auth/google            → verify Google id_token, upsert user
#   GET  /auth/me                → return current user (JWT required)
#   POST /auth/logout            → client-side logout hint
# =============================================================================

import os
from datetime import datetime, timezone, timedelta

import requests
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header
from pymongo.errors import DuplicateKeyError

from .db import users_col, farm_profiles_col, sessions_col
from .models import (
    SignupRequest,
    SigninRequest,
    GoogleAuthRequest,
    TokenResponse,
    MessageResponse,
)
from .utils import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    doc_to_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"


# ── Helper: require valid JWT ─────────────────────────────────────────────────
def _require_user(authorization: str) -> dict:
    """Extract Bearer token, validate JWT, return user document."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    doc = users_col().find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc



# =============================================================================
# GET /auth/config  — expose the Google Client ID safely from backend
# =============================================================================
@router.get("/config")
def get_auth_config():
    """Returns the Google OAuth client ID from backend .env (never hardcoded in frontend)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID not configured on server")
    return {"google_client_id": GOOGLE_CLIENT_ID}


# =============================================================================
# POST /auth/signup
# =============================================================================
@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    hashed = hash_password(req.password)
    now = datetime.now(timezone.utc)

    user_doc = {
        "name": req.name.strip(),
        "email": req.email.lower().strip(),
        "password_hash": hashed,
        "google_id": None,
        "phone": None,
        "preferred_language": req.language or "en",
        "created_at": now,
        "last_login": now,
        # Legacy fields for frontend context compatibility
        "location": req.location or "India",
        "photo_url": None,
    }

    try:
        result = users_col().insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered. Please sign in.")

    uid = result.inserted_id
    user_doc["_id"] = uid
    token = create_token(str(uid))

    # Create empty farm profile
    farm_profiles_col().insert_one({
        "user_id": uid,
        "district": None,
        "state": req.location or "India",
        "field_size_acres": None,
        "soil_type": None,
        "active_crop": None,
        "growth_stage": None,
        "soil_ph": None,
        "soil_npk": None,
        "location_coords": None,
        "updated_at": now
    })

    # Log session
    sessions_col().insert_one({
        "user_id": uid,
        "token_hash": hash_password(token),
        "device": "web",
        "expires_at": now + timedelta(days=7),
        "created_at": now
    })

    return TokenResponse(access_token=token, user=doc_to_user(user_doc))


# =============================================================================
# POST /auth/signin
# =============================================================================
@router.post("/signin", response_model=TokenResponse)
def signin(req: SigninRequest):
    doc = users_col().find_one({"email": req.email.lower().strip()})
    if not doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Google-only accounts have no password hash
    if not doc.get("password_hash"):
        raise HTTPException(
            status_code=400,
            detail="This account uses Google Sign-In. Please continue with Google."
        )

    if not verify_password(req.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    now = datetime.now(timezone.utc)
    # Touch last_login
    users_col().update_one(
        {"_id": doc["_id"]},
        {"$set": {"last_login": now}}
    )

    token = create_token(str(doc["_id"]))
    
    # Log session
    sessions_col().insert_one({
        "user_id": doc["_id"],
        "token_hash": hash_password(token),
        "device": "web",
        "expires_at": now + timedelta(days=7),
        "created_at": now
    })

    return TokenResponse(access_token=token, user=doc_to_user(doc))


# =============================================================================
# POST /auth/google  — verify id_token server-side, upsert user
# =============================================================================
@router.post("/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest):
    """
    Receives a Google id_token from the frontend.
    Verifies it against Google's tokeninfo endpoint.
    The GOOGLE_CLIENT_ID is never sent to the frontend — only used here for validation.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID not configured on server")

    # Verify the token with Google's tokeninfo endpoint
    resp = requests.get(
        GOOGLE_TOKEN_INFO_URL,
        params={"id_token": req.id_token},
        timeout=10,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    info = resp.json()

    # Validate audience — ensure token was issued for OUR app
    if info.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token audience mismatch")

    google_email = info.get("email", "").lower().strip()
    google_name  = info.get("name", google_email.split("@")[0].title())
    google_photo = info.get("picture")
    google_id    = info.get("sub")

    if not google_email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    now = datetime.now(timezone.utc)
    col = users_col()

    existing = col.find_one({"email": google_email})

    if existing:
        # Update name/photo if changed
        col.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "name": google_name,
                "photo_url": google_photo,
                "google_id": google_id,
                "last_login": now,
            }}
        )
        existing["name"]      = google_name
        existing["photo_url"] = google_photo
        doc = existing
    else:
        # New Google user — create with farm profile
        user_doc = {
            "name": google_name,
            "email": google_email,
            "password_hash": None,
            "google_id": google_id,
            "phone": None,
            "preferred_language": req.language or "en",
            "created_at": now,
            "last_login": now,
            # Legacy fields for frontend compatibility
            "location": req.location or "India",
            "photo_url": google_photo,
        }
        result = col.insert_one(user_doc)
        uid = result.inserted_id
        user_doc["_id"] = uid
        doc = user_doc

        farm_profiles_col().insert_one({
            "user_id": uid,
            "district": None,
            "state": req.location or "India",
            "field_size_acres": None,
            "soil_type": None,
            "active_crop": None,
            "growth_stage": None,
            "soil_ph": None,
            "soil_npk": None,
            "location_coords": None,
            "updated_at": now
        })

    token = create_token(str(doc["_id"]))
    
    sessions_col().insert_one({
        "user_id": doc["_id"],
        "token_hash": hash_password(token),
        "device": "web",
        "expires_at": now + timedelta(days=7),
        "created_at": now
    })

    return TokenResponse(access_token=token, user=doc_to_user(doc))


# =============================================================================
# GET /auth/me  — return current user from JWT
# =============================================================================
@router.get("/me", response_model=TokenResponse)
def get_me(authorization: str = Header(default="")):
    doc = _require_user(authorization)
    token = authorization.split(" ", 1)[1]
    return TokenResponse(access_token=token, user=doc_to_user(doc))


# =============================================================================
# POST /auth/logout  — stateless; client just discards its JWT
# =============================================================================
@router.post("/logout", response_model=MessageResponse)
def logout():
    return MessageResponse(message="Logged out successfully. Please discard your token.")
