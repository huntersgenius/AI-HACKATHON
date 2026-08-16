"""Patient-facing JSON API. HTTP only."""

from flask import Blueprint, request

from core.errors import ValidationError
from core.responses import ok
from services import doctor_service, message_service

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


# Doctor-side views of one patient. They live under /api/v1/patients/<pid>
# because that is the resource; the logic sits in doctor_service.
@bp.get("/<int:pid>/detail")
def detail(pid):
    return ok(doctor_service.get_patient_detail(pid))


@bp.get("/<int:pid>/timeline")
def timeline(pid):
    return ok({"items": doctor_service.get_timeline(pid)})


@bp.post("/<int:pid>/doctor-message")
def doctor_message(pid):
    payload = request.get_json(silent=True) or {}
    doctor_id = payload.get("doctor_id")
    if doctor_id is not None:
        try:
            doctor_id = int(doctor_id)
        except (TypeError, ValueError):
            raise ValidationError("Shifokor ID notoʻgʻri.")
    return ok(doctor_service.send_doctor_message(
        pid, payload.get("text"), doctor_id=doctor_id))
