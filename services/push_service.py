"""Subscribing/unsubscribing browsers for Web Push."""

from core.errors import ValidationError
from repos import push_subscription_repo

SUBSCRIBER_TYPES = ("patient", "doctor")


def subscribe(subscriber_type, subscriber_id, subscription):
    if subscriber_type not in SUBSCRIBER_TYPES:
        raise ValidationError("subscriber_type notoʻgʻri.")
    try:
        subscriber_id = int(subscriber_id)
    except (TypeError, ValueError):
        raise ValidationError("subscriber_id notoʻgʻri.")

    endpoint = (subscription or {}).get("endpoint")
    keys = (subscription or {}).get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not endpoint or not p256dh or not auth:
        raise ValidationError("Push obuna maʼlumotlari toʻliq emas.")

    push_subscription_repo.upsert(subscriber_type, subscriber_id, endpoint, p256dh, auth)
    return {"subscribed": True}


def unsubscribe(endpoint):
    if not endpoint:
        raise ValidationError("endpoint kerak.")
    push_subscription_repo.delete(endpoint)
    return {"subscribed": False}
