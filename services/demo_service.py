"""Demo controls: resetting to the seeded state and reading the event log.

`reset()` is the one sanctioned data-clearing path in the app (PLAN.md rule 4)
— it empties activity tables but never drops them, so the schema and the
seeded personas survive.
"""

import json

from repos import demo_repo, event_repo, patient_repo

DEFAULT_EVENT_LIMIT = 30
MAX_EVENT_LIMIT = 200


def reset():
    """Return the demo to its seeded state."""
    removed = demo_repo.clear_activity()
    demo_repo.reset_patients()
    demo_repo.reset_autoincrement()

    return {
        "removed": removed,
        "patients": [
            {
                "id": p["id"],
                "full_name": p["full_name"],
                "current_day": p["current_day"],
                "risk_level": p["risk_level"],
            }
            for p in patient_repo.list_all()
        ],
    }


def recent_events(limit=DEFAULT_EVENT_LIMIT):
    """Newest events first — the demo's 'look inside the machine' panel."""
    limit = max(1, min(int(limit or DEFAULT_EVENT_LIMIT), MAX_EVENT_LIMIT))

    items = []
    for row in event_repo.list_recent(limit):
        try:
            payload = json.loads(row["payload"] or "{}")
        except (TypeError, ValueError):
            payload = {}
        items.append({
            "id": row["id"],
            "event_name": row["event_name"],
            "payload": payload,
            "created_at": row["created_at"],
        })
    return items
