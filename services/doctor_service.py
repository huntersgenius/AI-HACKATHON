"""Data the doctor's dashboard needs.

Shapes repo rows into the payloads the panel polls for. Sorting puts the
patients who need attention at the top — red first, then yellow.
"""

import json

from analyzers.base import RISK_ORDER
from core.errors import NotFound
from repos import alert_repo, assessment_repo, doctor_repo, patient_repo


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def _parse_signals(raw):
    try:
        signals = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return signals if isinstance(signals, list) else []


def get_doctor(doctor_id):
    doctor = doctor_repo.get(doctor_id)
    if doctor is None:
        raise NotFound("Shifokor topilmadi.")
    return doctor


def list_patients(doctor_id):
    """Patient list with risk level, last activity and latest reasoning."""
    get_doctor(doctor_id)

    patients = []
    for row in patient_repo.list_by_doctor(doctor_id):
        item = _as_dict(row)
        latest = assessment_repo.latest_for_patient(row["id"])
        item["latest_assessment"] = None
        if latest is not None:
            item["latest_assessment"] = {
                "id": latest["id"],
                "risk_level": latest["risk_level"],
                "risk_score": latest["risk_score"],
                "reasoning": latest["reasoning"],
                "recommended_action": latest["recommended_action"],
                "danger_signals": _parse_signals(latest["danger_signals"]),
                "created_at": latest["created_at"],
            }
        patients.append(item)

    # Riskiest first; within a level, the most recently active patient leads.
    # Two stable passes, because the two keys sort in opposite directions.
    patients.sort(key=lambda p: p["last_message_at"] or "", reverse=True)
    patients.sort(key=lambda p: RISK_ORDER.get(p["risk_level"], 0), reverse=True)
    return patients


def list_alerts(doctor_id, status=None):
    get_doctor(doctor_id)
    return [_as_dict(r) for r in alert_repo.list_for_doctor(doctor_id, status=status)]


def get_dashboard(doctor_id):
    doctor = get_doctor(doctor_id)
    patients = list_patients(doctor_id)
    return {
        "doctor": _as_dict(doctor),
        "patients": patients,
        "counts": {
            "total": len(patients),
            "red": sum(1 for p in patients if p["risk_level"] == "red"),
            "yellow": sum(1 for p in patients if p["risk_level"] == "yellow"),
            "green": sum(1 for p in patients if p["risk_level"] == "green"),
            "new_alerts": alert_repo.count_by_status(doctor_id, "new"),
        },
    }
