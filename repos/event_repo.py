"""SQL for the `event_log` table.

`core/events.py` writes through here so that rule 1 holds everywhere: SQL for
application data lives only in `repos/`.
"""

from core import db


def create(event_name, payload_json="{}"):
    return db.execute(
        "INSERT INTO event_log (event_name, payload) VALUES (?, ?)",
        (event_name, payload_json),
    )


def list_recent(limit=50):
    return db.query_all(
        "SELECT * FROM event_log ORDER BY id DESC LIMIT ?", (limit,))


def count():
    return db.query_value("SELECT COUNT(*) FROM event_log", default=0)
