"""SQL for the `ai_assessments` table.

`danger_signals` and `analyzer_results` are stored as JSON text — callers pass
already-serialised strings, so this layer stays pure SQL.
"""

from core import db


def get(assessment_id):
    return db.query_one(
        "SELECT * FROM ai_assessments WHERE id = ?", (assessment_id,))


def create(patient_id, risk_level, risk_score=0, checkin_id=None,
           message_id=None, danger_signals="[]", reasoning=None,
           recommended_action=None, analyzer_results="{}", source="llm"):
    return db.execute(
        """
        INSERT INTO ai_assessments (
            patient_id, checkin_id, message_id, risk_level, risk_score,
            danger_signals, reasoning, recommended_action, analyzer_results,
            source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (patient_id, checkin_id, message_id, risk_level, risk_score,
         danger_signals, reasoning, recommended_action, analyzer_results,
         source),
    )


def latest_for_patient(patient_id):
    return db.query_one(
        """
        SELECT * FROM ai_assessments
         WHERE patient_id = ?
         ORDER BY id DESC
         LIMIT 1
        """,
        (patient_id,),
    )


def list_for_patient(patient_id, limit=200):
    return db.query_all(
        """
        SELECT * FROM ai_assessments
         WHERE patient_id = ?
         ORDER BY id
         LIMIT ?
        """,
        (patient_id, limit),
    )


def get_by_message(message_id):
    return db.query_one(
        "SELECT * FROM ai_assessments WHERE message_id = ?", (message_id,))


def trend_for_patient(patient_id, limit=100):
    """risk_score over time — the data behind the trend chart."""
    return db.query_all(
        """
        SELECT id, risk_score, risk_level, created_at
          FROM ai_assessments
         WHERE patient_id = ?
         ORDER BY id
         LIMIT ?
        """,
        (patient_id, limit),
    )
