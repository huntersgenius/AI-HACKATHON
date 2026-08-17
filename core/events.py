"""In-process event bus (PLAN.md section 4.2).

Services announce what happened with `emit()`; reactions live in `hooks/` and
subscribe with `@on(...)`. A new reaction is a new file in `hooks/` — services
never grow an `if` for it.

Every emit is written to `event_log` (demo transparency + audit), and a failing
handler is logged and skipped so the main request always finishes.
"""

import json
from collections import defaultdict

from flask import current_app

_handlers = defaultdict(list)


# Known event names (PLAN.md section 4.2). Kept as constants so typos in a
# hook surface as an import error instead of silence.
CHECKIN_SENT = "checkin.sent"
CHECKIN_ANSWERED = "checkin.answered"
ASSESSMENT_CREATED = "assessment.created"
ALERT_RAISED = "alert.raised"
ALERT_RESOLVED = "alert.resolved"
DOCTOR_REPLIED = "doctor.replied"
CALL_PLACED = "call.placed"
CALL_FAILED = "call.failed"


def on(event_name):
    """Decorator: register `fn` as a handler for `event_name`."""

    def wrap(fn):
        _handlers[event_name].append(fn)
        return fn

    return wrap


def handlers(event_name):
    return list(_handlers.get(event_name, []))


def registered_events():
    return {name: len(fns) for name, fns in _handlers.items() if fns}


def _log(message, *args):
    try:
        current_app.logger.exception(message, *args)
    except RuntimeError:  # no app context (tests, scripts)
        pass


def log_event(event_name, payload):
    """Persist one event row. Never raises — logging must not break a flow."""
    from repos import event_repo  # local import: repos import core.db

    try:
        event_repo.create(
            event_name,
            json.dumps(payload, ensure_ascii=False, default=str),
        )
    except Exception:
        _log("event_log write failed: %s", event_name)


def emit(event_name, **payload):
    """Log the event, then run every handler in isolation."""
    log_event(event_name, payload)
    for fn in _handlers.get(event_name, []):
        try:
            fn(**payload)
        except Exception:
            _log("hook failed: %s -> %s", event_name, getattr(fn, "__name__", fn))
