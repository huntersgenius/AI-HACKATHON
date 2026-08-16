"""SQL for the `messages` table.

`list_after` powers incremental polling: the client sends the last id it has
and only newer rows come back, so the chat stays fast as history grows.
"""

from core import db


def get(message_id):
    return db.query_one("SELECT * FROM messages WHERE id = ?", (message_id,))


def create(patient_id, sender, text, checkin_id=None, meta_json="{}"):
    return db.execute(
        """
        INSERT INTO messages (patient_id, checkin_id, sender, text, meta_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patient_id, checkin_id, sender, text, meta_json),
    )


def list_for_patient(patient_id, limit=200):
    return db.query_all(
        """
        SELECT * FROM messages
         WHERE patient_id = ?
         ORDER BY id
         LIMIT ?
        """,
        (patient_id, limit),
    )


def list_after(patient_id, after_id=0, limit=200):
    return db.query_all(
        """
        SELECT * FROM messages
         WHERE patient_id = ? AND id > ?
         ORDER BY id
         LIMIT ?
        """,
        (patient_id, after_id or 0, limit),
    )


def last_id(patient_id):
    return db.query_value(
        "SELECT MAX(id) FROM messages WHERE patient_id = ?",
        (patient_id,),
        default=0,
    ) or 0


def last_activity_at(patient_id):
    return db.query_value(
        "SELECT MAX(created_at) FROM messages WHERE patient_id = ?",
        (patient_id,),
    )


def count_for_patient(patient_id):
    return db.query_value(
        "SELECT COUNT(*) FROM messages WHERE patient_id = ?",
        (patient_id,),
        default=0,
    )
