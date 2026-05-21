# =============================================================================
# backend/auth/models.py — Pydantic request / response models
# =============================================================================
from pydantic import BaseModel, EmailStr
from typing import Optional, Any


# ── Request models ────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    language: Optional[str] = "en"
    location: Optional[str] = "India"


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str
    language: Optional[str] = "en"
    location: Optional[str] = "India"


# ── Response models ───────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    language: str
    location: str
    photo_url: Optional[str] = None
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageResponse(BaseModel):
    message: str
