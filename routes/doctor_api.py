"""Doctor-facing JSON API. HTTP only."""

from flask import Blueprint, request

from core.errors import ValidationError
from core.responses import ok
from services import doctor_service

bp = Blueprint("doctor_api", __name__)

ALERT_STATUSES = ("new", "seen", "resolved")


@bp.get("/<int:did>/patients")
def list_patients(did):
    return ok({"patients": doctor_service.list_patients(did)})


@bp.get("/<int:did>/alerts")
def list_alerts(did):
    status = request.args.get("status") or None
    if status and status not in ALERT_STATUSES:
        raise ValidationError("Signal holati notoʻgʻri.")
    return ok({"alerts": doctor_service.list_alerts(did, status=status)})


@bp.get("/<int:did>/dashboard")
def dashboard(did):
    return ok(doctor_service.get_dashboard(did))
