"""SQL for the `patients` table."""

from core import db


def get(patient_id):
    return db.query_one("SELECT * FROM patients WHERE id = ?", (patient_id,))


def list_all():
    return db.query_all("SELECT * FROM patients ORDER BY id")


def list_by_doctor(doctor_id):
    """Patients of one doctor, with their last activity — dashboard list."""
    return db.query_all(
        """
        SELECT p.*,
               (SELECT MAX(created_at) FROM messages m
                 WHERE m.patient_id = p.id)            AS last_message_at,
               (SELECT COUNT(*) FROM alerts a
                 WHERE a.patient_id = p.id
                   AND a.status = 'new')               AS open_alerts
          FROM patients p
         WHERE p.doctor_id = ?
         ORDER BY p.id
        """,
        (doctor_id,),
    )


def create(full_name, persona_key, doctor_id, diagnosis=None,
           discharge_date=None, phone_sim=None, meta_json="{}"):
    return db.execute(
        """
        INSERT INTO patients (full_name, persona_key, diagnosis, discharge_date,
                              phone_sim, doctor_id, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (full_name, persona_key, diagnosis, discharge_date, phone_sim,
         doctor_id, meta_json),
    )


def set_current_day(patient_id, day_number):
    db.execute(
        "UPDATE patients SET current_day = ? WHERE id = ?",
        (day_number, patient_id),
    )


def set_risk_level(patient_id, risk_level):
    db.execute(
        "UPDATE patients SET risk_level = ? WHERE id = ?",
        (risk_level, patient_id),
    )


def set_meta_json(patient_id, meta_json):
    db.execute(
        "UPDATE patients SET meta_json = ? WHERE id = ?",
        (meta_json, patient_id),
    )
