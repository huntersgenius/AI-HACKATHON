"""Alert actions. HTTP only."""

from flask import Blueprint

from core.responses import ok
from services import doctor_service

bp = Blueprint("alert_api", __name__)


@bp.post("/<int:aid>/resolve")
def resolve(aid):
    return ok({"alert": doctor_service.resolve_alert(aid)})
