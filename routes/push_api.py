"""Web Push subscription endpoints. HTTP only."""

from flask import Blueprint, request

from config import Config
from core.responses import ok
from services import push_service

bp = Blueprint("push_api", __name__)


@bp.get("/vapid-public-key")
def vapid_public_key():
    return ok({"key": Config.VAPID_PUBLIC_KEY})


@bp.post("/subscribe")
def subscribe():
    payload = request.get_json(silent=True) or {}
    return ok(push_service.subscribe(
        payload.get("subscriber_type"),
        payload.get("subscriber_id"),
        payload.get("subscription"),
    ))


@bp.post("/unsubscribe")
def unsubscribe():
    payload = request.get_json(silent=True) or {}
    return ok(push_service.unsubscribe(payload.get("endpoint")))
