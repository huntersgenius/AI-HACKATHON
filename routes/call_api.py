"""Voice-call actions. HTTP only."""

from flask import Blueprint, request

from core.responses import ok
from services import call_service

bp = Blueprint("call_api", __name__)


@bp.get("/<int:pid>/calls")
def list_calls(pid):
    return ok({"calls": call_service.list_calls(pid)})


@bp.post("/<int:pid>/calls")
def place_call(pid):
    payload = request.get_json(silent=True) or {}
    doctor_id = payload.get("doctor_id")
    return ok({"call": call_service.place_call(pid, doctor_id=doctor_id)})
