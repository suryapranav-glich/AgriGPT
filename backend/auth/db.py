# =============================================================================
# backend/auth/db.py — MongoDB connection & helper collections
# =============================================================================
import os
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()["agrigpt"]


def users_col() -> Collection:
    col = get_db()["users"]
    col.create_index([("email", ASCENDING)], unique=True, background=True)
    return col


def farm_profiles_col() -> Collection:
    col = get_db()["farm_profiles"]
    col.create_index([("user_id", ASCENDING)], unique=True, background=True)
    return col


def disease_diagnoses_col() -> Collection:
    col = get_db()["disease_diagnoses"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def chat_history_col() -> Collection:
    col = get_db()["chat_history"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def soil_reports_col() -> Collection:
    col = get_db()["soil_reports"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def irrigation_logs_col() -> Collection:
    col = get_db()["irrigation_logs"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def market_queries_col() -> Collection:
    col = get_db()["market_queries"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def scheme_queries_col() -> Collection:
    col = get_db()["scheme_queries"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def sessions_col() -> Collection:
    col = get_db()["sessions"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col


def voice_queries_col() -> Collection:
    col = get_db()["voice_queries"]
    col.create_index([("user_id", ASCENDING)], background=True)
    return col
