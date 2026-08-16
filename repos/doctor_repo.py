"""SQL for the `doctors` table."""

from core import db


def get(doctor_id):
    return db.query_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,))


def list_all():
    return db.query_all("SELECT * FROM doctors ORDER BY id")


def create(full_name, clinic_name, phone_sim=None):
    return db.execute(
        "INSERT INTO doctors (full_name, clinic_name, phone_sim) VALUES (?, ?, ?)",
        (full_name, clinic_name, phone_sim),
    )
