"""Claude-based triage analyzer.

The prompt lives in `prompts/*.txt`; the response shape is pinned with a JSON
schema (`output_config.format`), so the model cannot answer with prose.

Nothing here is trusted: a missing key, a disabled flag, a timeout, an API
error or a malformed payload all return None. The pipeline then merges
whatever the rule analyzer produced, so the demo never depends on the network.
"""

import json

from config import Config, features
from core import prompts
from analyzers.base import GREEN, RED, YELLOW, AnalyzerResult, analyzer

VALID_LEVELS = (GREEN, YELLOW, RED)

# Pins the reply shape — this is a contract, not prompt text.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string", "enum": list(VALID_LEVELS)},
        "risk_score": {"type": "integer"},
        "danger_signals": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
        "recommended_action": {"type": "string"},
    },
    "required": [
        "risk_level", "risk_score", "danger_signals", "reasoning",
        "recommended_action",
    ],
    "additionalProperties": False,
}

DEFAULT_SCORE = {GREEN: 15, YELLOW: 55, RED: 90}
MAX_TOKENS = 2048


def _log_exception(message, *args):
    from flask import current_app
    try:
        current_app.logger.exception(message, *args)
    except RuntimeError:
        pass


def _client():
    """Build a client, or None when the SDK or the key is unavailable."""
    api_key = Config.ANTHROPIC_API_KEY
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic(
        api_key=api_key,
        timeout=float(Config.LLM_TIMEOUT_SECONDS),
        max_retries=0,  # the demo prefers a fast fallback over a slow retry
    )


def _build_case(context):
    """The per-request user turn: this patient, this day, this answer."""
    return prompts.render(
        Config.TRIAGE_CASE_PROMPT,
        diagnosis=context.get("diagnosis") or "nomaʼlum",
        day_number=context.get("day_number") or "?",
        question_key=context.get("question_key") or "umumiy",
        question_text=context.get("question_text") or "-",
        answer_text=context.get("text") or "",
    )


def _first_text(message):
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "text":
            return block.text
    return None


def _coerce_score(raw, level):
    try:
        score = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_SCORE[level]
    return max(0, min(100, score))


def _coerce_signals(raw):
    if not isinstance(raw, list):
        return []
    return [str(s).strip() for s in raw if str(s).strip()]


def parse_response(text):
    """Turn raw model output into an AnalyzerResult, or None if unusable."""
    if not text:
        return None
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    level = str(payload.get("risk_level", "")).strip().lower()
    if level not in VALID_LEVELS:
        return None

    action = str(payload.get("recommended_action") or "").strip() or None
    return AnalyzerResult(
        risk_level=level,
        risk_score=_coerce_score(payload.get("risk_score"), level),
        danger_signals=_coerce_signals(payload.get("danger_signals")),
        reasoning=str(payload.get("reasoning") or "").strip(),
        recommended_action=action,
    )


@analyzer("llm", priority=20)
def analyze(context):
    if not features.enabled("llm_analyzer"):
        return None
    if not (context.get("text") or "").strip():
        return None

    client = _client()
    if client is None:
        return None

    try:
        message = client.messages.create(
            model=Config.LLM_MODEL,
            max_tokens=MAX_TOKENS,
            system=prompts.load(Config.TRIAGE_PROMPT),
            messages=[{"role": "user", "content": _build_case(context)}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA},
            },
        )
    except Exception:
        # Timeout, network failure, bad key, rate limit — all the same to us.
        _log_exception("llm analyzer call failed")
        return None

    try:
        return parse_response(_first_text(message))
    except Exception:
        _log_exception("llm analyzer response parsing failed")
        return None
