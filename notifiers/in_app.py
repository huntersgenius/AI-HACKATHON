"""In-app notifier: nothing to deliver, the panel already polls for alerts.

Registered mainly so `notifiers.REGISTRY` is never empty and other code can
look channels up uniformly. `send()` just drops a line in `event_log` so it
shows up in the demo events panel like every other channel.
"""

from core import events
from notifiers.base import register


class InAppNotifier:
    key = "in_app"

    def send(self, to, title, body):
        events.log_event("notify.in_app", {"to": to, "title": title, "body": body})


register(InAppNotifier())
