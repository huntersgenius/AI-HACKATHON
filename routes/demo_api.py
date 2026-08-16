"""Demo control endpoints. HTTP only — the work happens in services/."""

from flask import Blueprint, request

from core.errors import ValidationError
from core.responses import ok
from services import checkin_service, demo_service

bp = Blueprint("demo_api", __name__)


def _required_int(payload, key, error_message):
    value = payload.get(key)
    if value is None or value == "":
        raise ValidationError(error_message)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(error_message)


@bp.post("/advance-day")
def advance_day():
    payload = request.get_json(silent=True) or {}
    patient_id = _required_int(payload, "patient_id", "Bemor ID ko'rsatilmagan.")
    return ok(checkin_service.advance_day(patient_id))


@bp.post("/reset")
def reset():
    return ok(demo_service.reset())


@bp.get("/events")
def events():
    limit = request.args.get("limit")
    try:
        limit = int(limit) if limit else None
    except (TypeError, ValueError):
        raise ValidationError("limit notoʻgʻri.")
    return ok({"events": demo_service.recent_events(limit)})
