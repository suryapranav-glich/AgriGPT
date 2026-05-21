# =============================================================================
# backend/auth/utils.py — JWT creation/verification & password hashing
#
# Uses bcrypt library directly (not passlib) for Python 3.14 + bcrypt 5.x
# compatibility. passlib 1.7.4 is incompatible with bcrypt >= 4.x.
# =============================================================================

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from .models import UserOut

# ── Password hashing (direct bcrypt — no passlib) ─────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    # Truncate to 72 bytes — bcrypt's hard limit; avoids ValueError in bcrypt >= 4
    password_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    password_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ── JWT helpers ───────────────────────────────────────────────────────────────
SECRET     = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days


def create_token(user_id: str) -> str:
    """Create a signed JWT that expires after EXPIRE_MIN minutes."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MIN)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    """Decode JWT and return the user_id (sub) or None on failure."""
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ── MongoDB doc → UserOut ─────────────────────────────────────────────────────
def doc_to_user(doc: dict) -> UserOut:
    """Convert a MongoDB user document to a safe UserOut response model."""
    return UserOut(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        email=doc.get("email", ""),
        language=doc.get("language", "en"),
        location=doc.get("location", "India"),
        photo_url=doc.get("photo_url"),
        created_at=str(doc.get("created_at", "")),
    )
