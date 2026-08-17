"""SQL for the demo reset.

The only place that clears data. Tables are emptied, never dropped — the
schema and the seeded personas/questions come from migrations and must
survive a reset.
"""

from core import db

# Child rows first so foreign keys stay satisfied.
RESET_TABLES = (
    "alerts",
    "ai_assessments",
    "messages",
    "checkins",
    "event_log",
)


def clear_activity():
    """Delete everything the demo generates; returns rows removed per table."""
    removed = {}
    for table in RESET_TABLES:
        removed[table] = db.query_value(
            "SELECT COUNT(*) FROM %s" % table, default=0)
        db.execute("DELETE FROM %s" % table)
    return removed


def reset_patients():
    """Put every patient back to day 0 and green."""
    db.execute(
        "UPDATE patients SET current_day = 0, risk_level = 'green'")


def reset_autoincrement():
    """Restart ids so a fresh demo reads 1, 2, 3 rather than 47, 48, 49."""
    db.execute(
        "DELETE FROM sqlite_sequence WHERE name IN "
        "('alerts', 'ai_assessments', 'messages', 'checkins', 'event_log')")
