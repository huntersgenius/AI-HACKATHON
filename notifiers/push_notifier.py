"""Web Push channel (VAPID). Delivers to phones even when the tab is closed.

Sends to every subscription stored for a subscriber; a dead endpoint (410/404
— the user uninstalled, cleared data, etc.) is pruned automatically. Like
every other network channel here, a missing key or a send failure is logged
and swallowed — push is a convenience layer on top of polling, never a thing
the app depends on to function.
"""

import json

from config import Config, features
from notifiers.base import register
from repos import push_subscription_repo


def _log_exception(message, *args):
    from flask import current_app
    try:
        current_app.logger.exception(message, *args)
    except RuntimeError:
        pass


def _configured():
    return bool(Config.VAPID_PUBLIC_KEY and Config.VAPID_PRIVATE_KEY)


def send_to_subscriber(subscriber_type, subscriber_id, title, body, url=None):
    """Push `title`/`body` to every device subscribed for this patient/doctor."""
    if not features.enabled("push_notifications") or not _configured():
        return

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        _log_exception("pywebpush not installed")
        return

    payload = json.dumps({"title": title, "body": body, "url": url or "/"},
                          ensure_ascii=False)

    for sub in push_subscription_repo.list_for(subscriber_type, subscriber_id):
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=Config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:%s" % Config.VAPID_CONTACT_EMAIL},
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                push_subscription_repo.delete(sub["endpoint"])
            else:
                _log_exception("push send failed: %s", exc)
        except Exception as exc:
            _log_exception("push send failed: %s", exc)


class PushNotifier:
    key = "push"

    def send(self, to, title, body):
        subscriber_type, _, subscriber_id = str(to).partition(":")
        send_to_subscriber(subscriber_type, int(subscriber_id), title, body)


register(PushNotifier())
