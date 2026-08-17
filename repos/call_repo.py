"""SQL for the `call_log` table."""

from core import db


def get(call_id):
    return db.query_one("SELECT * FROM call_log WHERE id = ?", (call_id,))


def create(patient_id, phone, doctor_id=None, alert_id=None, trigger="manual"):
    return db.execute(
        """
        INSERT INTO call_log (patient_id, doctor_id, alert_id, phone, trigger)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patient_id, doctor_id, alert_id, phone, trigger),
    )


def mark_queued(call_id, external_call_id):
    db.execute(
        """
        UPDATE call_log
           SET status = 'pending', external_call_id = ?, updated_at = datetime('now')
         WHERE id = ?
        """,
        (external_call_id, call_id),
    )


def mark_failed(call_id, error_code):
    db.execute(
        """
        UPDATE call_log
           SET status = 'failed', error_code = ?, updated_at = datetime('now')
         WHERE id = ?
        """,
        (error_code, call_id),
    )


def update_status(call_id, status, answered=None, duration_seconds=None, pressed_one=None):
    db.execute(
        """
        UPDATE call_log
           SET status = ?, answered = ?, duration_seconds = ?, pressed_one = ?,
               updated_at = datetime('now')
         WHERE id = ?
        """,
        (status, answered, duration_seconds, pressed_one, call_id),
    )


def list_for_patient(patient_id, limit=20):
    return db.query_all(
        """
        SELECT * FROM call_log
         WHERE patient_id = ?
         ORDER BY id DESC
         LIMIT ?
        """,
        (patient_id, limit),
    )


def list_pending(limit=50):
    """Calls whose status we haven't confirmed with the provider yet."""
    return db.query_all(
        """
        SELECT * FROM call_log
         WHERE status = 'pending' AND external_call_id IS NOT NULL
         ORDER BY id
         LIMIT ?
        """,
        (limit,),
    )


def recent_call_for_phone(phone, within_seconds=60):
    """Guards against smartcall.uz's `duplicate_call` error before we even ask."""
    return db.query_one(
        """
        SELECT * FROM call_log
         WHERE phone = ?
           AND created_at >= datetime('now', ?)
         ORDER BY id DESC
         LIMIT 1
        """,
        (phone, "-%d seconds" % within_seconds),
    )
