"""SQL for the `alerts` table."""

from core import db


def get(alert_id):
    return db.query_one("SELECT * FROM alerts WHERE id = ?", (alert_id,))


def create(patient_id, doctor_id, title, severity="yellow", assessment_id=None):
    return db.execute(
        """
        INSERT INTO alerts (patient_id, doctor_id, assessment_id, severity, title)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patient_id, doctor_id, assessment_id, severity, title),
    )


def list_for_doctor(doctor_id, status=None, limit=100):
    """Alerts of one doctor, newest first; optionally filtered by status."""
    if status:
        return db.query_all(
            """
            SELECT a.*, p.full_name AS patient_name, p.risk_level AS patient_risk
              FROM alerts a
              JOIN patients p ON p.id = a.patient_id
             WHERE a.doctor_id = ? AND a.status = ?
             ORDER BY a.id DESC
             LIMIT ?
            """,
            (doctor_id, status, limit),
        )
    return db.query_all(
        """
        SELECT a.*, p.full_name AS patient_name, p.risk_level AS patient_risk
          FROM alerts a
          JOIN patients p ON p.id = a.patient_id
         WHERE a.doctor_id = ?
         ORDER BY a.id DESC
         LIMIT ?
        """,
        (doctor_id, limit),
    )


def list_for_patient(patient_id, limit=100):
    return db.query_all(
        """
        SELECT * FROM alerts
         WHERE patient_id = ?
         ORDER BY id DESC
         LIMIT ?
        """,
        (patient_id, limit),
    )


def count_by_status(doctor_id, status="new"):
    return db.query_value(
        "SELECT COUNT(*) FROM alerts WHERE doctor_id = ? AND status = ?",
        (doctor_id, status),
        default=0,
    )


def mark_seen(alert_id):
    db.execute("UPDATE alerts SET status = 'seen' WHERE id = ?", (alert_id,))


def resolve(alert_id):
    db.execute(
        """
        UPDATE alerts
           SET status = 'resolved', resolved_at = datetime('now')
         WHERE id = ?
        """,
        (alert_id,),
    )
