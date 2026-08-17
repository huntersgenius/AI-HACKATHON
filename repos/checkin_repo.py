"""SQL for `checkins` and `checkin_templates`.

Templates are looked up by (persona_key, day_offset) — no persona is ever
named in Python, which is what keeps "new persona = new SQL row" true.
"""

from core import db


# --- checkin_templates ---------------------------------------------------

def templates_for_day(persona_key, day_offset):
    """Every question for one persona-day, in `seq` order."""
    return db.query_all(
        """
        SELECT * FROM checkin_templates
         WHERE persona_key = ? AND day_offset = ?
         ORDER BY seq, id
        """,
        (persona_key, day_offset),
    )


def get_template(template_id):
    return db.query_one(
        "SELECT * FROM checkin_templates WHERE id = ?", (template_id,))


def max_day_offset(persona_key):
    """Highest configured day for a persona — the end of the follow-up plan."""
    return db.query_value(
        "SELECT MAX(day_offset) FROM checkin_templates WHERE persona_key = ?",
        (persona_key,),
        default=0,
    ) or 0


def list_templates(persona_key):
    return db.query_all(
        """
        SELECT * FROM checkin_templates
         WHERE persona_key = ?
         ORDER BY day_offset, seq, id
        """,
        (persona_key,),
    )


# --- checkins ------------------------------------------------------------

def get(checkin_id):
    return db.query_one("SELECT * FROM checkins WHERE id = ?", (checkin_id,))


def create(patient_id, template_id, day_number, status="pending"):
    return db.execute(
        """
        INSERT INTO checkins (patient_id, template_id, day_number, status)
        VALUES (?, ?, ?, ?)
        """,
        (patient_id, template_id, day_number, status),
    )


def list_for_patient(patient_id):
    return db.query_all(
        """
        SELECT c.*, t.question_key, t.question_text, t.answer_type, t.config_json
          FROM checkins c
     LEFT JOIN checkin_templates t ON t.id = c.template_id
         WHERE c.patient_id = ?
         ORDER BY c.day_number, c.id
        """,
        (patient_id,),
    )


def oldest_pending(patient_id):
    """The question the patient still owes an answer to, if any."""
    return db.query_one(
        """
        SELECT c.*, t.question_key, t.question_text, t.answer_type, t.config_json
          FROM checkins c
     LEFT JOIN checkin_templates t ON t.id = c.template_id
         WHERE c.patient_id = ? AND c.status = 'pending'
         ORDER BY c.day_number, c.id
         LIMIT 1
        """,
        (patient_id,),
    )


def exists_for_day(patient_id, day_number):
    """Guard against sending the same day twice."""
    return db.query_value(
        "SELECT COUNT(*) FROM checkins WHERE patient_id = ? AND day_number = ?",
        (patient_id, day_number),
        default=0,
    ) > 0


def mark_answered(checkin_id):
    db.execute(
        """
        UPDATE checkins
           SET status = 'answered', answered_at = datetime('now')
         WHERE id = ?
        """,
        (checkin_id,),
    )


def mark_skipped(checkin_id):
    db.execute(
        "UPDATE checkins SET status = 'skipped' WHERE id = ?", (checkin_id,))
