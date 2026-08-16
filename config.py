"""Application configuration and feature flags.

Everything the app needs to know about its environment is read here, once.
Other modules read config through the Flask app config or through
`features.enabled(...)` — they never touch os.environ directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# PLAN.md section 7. An unfinished feature is merged with its flag off.
FEATURES = {
    "llm_analyzer": True,    # False -> rule analyzer only (offline demo)
    "doctor_reply": True,
    "trend_chart": True,     # ready as of phase 9
    "sms_notifier": False,   # roadmap
    "multi_question": False,  # several questions in one day
}


def _env_bool(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_features():
    """FEATURES defaults, each one overridable by FEATURE_<NAME> in the env."""
    resolved = {}
    for key, default in FEATURES.items():
        resolved[key] = _env_bool("FEATURE_" + key.upper(), default)
    return resolved


class Features:
    """Tiny read-only wrapper so call sites read as `features.enabled('x')`."""

    def __init__(self, flags):
        self._flags = dict(flags)

    def enabled(self, name):
        return bool(self._flags.get(name, False))

    def as_dict(self):
        return dict(self._flags)


def _db_path():
    raw = os.environ.get("DB_PATH", "hamroh.db")
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


class Config:
    PROJECT_ROOT = str(BASE_DIR)

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DEBUG = _env_bool("FLASK_DEBUG", True)
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = _env_int("PORT", 5000)

    DB_PATH = _db_path()
    MIGRATIONS_DIR = str(BASE_DIR / "migrations")
    PROMPTS_DIR = str(BASE_DIR / "prompts")

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "claude-opus-5")
    LLM_TIMEOUT_SECONDS = _env_int("LLM_TIMEOUT_SECONDS", 10)
    TRIAGE_PROMPT = os.environ.get("TRIAGE_PROMPT", "triage_v1.txt")
    TRIAGE_CASE_PROMPT = os.environ.get(
        "TRIAGE_CASE_PROMPT", "triage_v1_case.txt")

    FEATURES = _resolve_features()


features = Features(Config.FEATURES)
