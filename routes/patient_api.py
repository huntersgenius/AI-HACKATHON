"""Patient-facing JSON API. HTTP only."""

from flask import Blueprint, request

from core.errors import ValidationError
from core.responses import ok
from services import message_service

bp = Blueprint("patient_api", __name__)


@bp.get("/<int:pid>/messages")
def list_messages(pid):
    try:
        after_id = int(request.args.get("after_id", 0) or 0)
    except (TypeError, ValueError):
        raise ValidationError("after_id noto'g'ri.")
    messages = message_service.list_messages(pid, after_id=after_id)
    return ok({"messages": messages})


@bp.post("/<int:pid>/messages")
def create_message(pid):
    payload = request.get_json(silent=True) or {}
    return ok(message_service.receive_patient_message(pid, payload.get("text")))


@bp.get("/<int:pid>/status")
def status(pid):
    return ok(message_service.get_status(pid))
