"""Notifier registry (PLAN.md section 4.3).

A notifier is anything that can push a message to a human outside the app.
Each channel implements `send(to, title, body)` and registers itself with
`register()`. Callers look a channel up by key (`REGISTRY['call']`) instead
of importing a specific module, so adding SMS/telegram/email later never
touches the call sites.
"""

from typing import Protocol


class Notifier(Protocol):
    key: str

    def send(self, to, title, body):
        ...


REGISTRY = {}


def register(notifier):
    REGISTRY[notifier.key] = notifier
    return notifier


def get(key):
    return REGISTRY.get(key)
