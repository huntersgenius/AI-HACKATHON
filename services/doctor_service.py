"""Data the doctor's dashboard needs.

Shapes repo rows into the payloads the panel polls for. Sorting puts the
patients who need attention at the top — red first, then yellow.
"""

import json

from analyzers.base import RISK_ORDER
from config import features
from core import events
from core.errors import FeatureDisabled, NotFound, ValidationError
from repos import (alert_repo, assessment_repo, checkin_repo, doctor_repo,
                   message_repo, patient_repo)

MAX_MESSAGE_LENGTH = 2000


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


def _get_patient(patient_id):
    patient = patient_repo.get(patient_id)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


def get_patient_detail(patient_id):
    """Header data for the patient detail page."""
    patient = _get_patient(patient_id)
    doctor = doctor_repo.get(patient["doctor_id"])
    latest = assessment_repo.latest_for_patient(patient_id)
    pending = checkin_repo.oldest_pending(patient_id)

    return {
        "patient": _as_dict(patient),
        "doctor": _as_dict(doctor) if doctor is not None else None,
        "latest_assessment": _as_dict(latest) if latest is not None else None,
        "open_alerts": alert_repo.count_by_status(patient["doctor_id"], "new"),
        "pending_question": pending["question_text"] if pending is not None else None,
    }


def get_timeline(patient_id):
    """Messages and assessments woven into one chronological history."""
    _get_patient(patient_id)

    items = []
    for row in message_repo.list_for_patient(patient_id):
        items.append({
            "kind": "message",
            "id": row["id"],
            "sender": row["sender"],
            "text": row["text"],
            "checkin_id": row["checkin_id"],
            "created_at": row["created_at"],
        })

    for row in assessment_repo.list_for_patient(patient_id):
        items.append({
            "kind": "assessment",
            "id": row["id"],
            "message_id": row["message_id"],
            "risk_level": row["risk_level"],
            "risk_score": row["risk_score"],
            "danger_signals": _parse_signals(row["danger_signals"]),
            "reasoning": row["reasoning"],
            "recommended_action": row["recommended_action"],
            "source": row["source"],
            "created_at": row["created_at"],
        })

    # created_at only has second granularity, so a message and the assessment
    # it triggered usually carry the identical timestamp. Sorting on time
    # alone would drop every assessment to the bottom, so each item is
    # anchored to the message it belongs to (its own id, or the message_id it
    # analysed) and the assessment sorts just after that message.
    def position(item):
        if item["kind"] == "message":
            return (item["created_at"] or "", item["id"], 0, item["id"])
        anchor = item["message_id"] or 0
        return (item["created_at"] or "", anchor, 1, item["id"])

    items.sort(key=position)
    return items


def send_doctor_message(patient_id, text, doctor_id=None):
    """Store a message from the doctor and announce it to the patient chat."""
    if not features.enabled("doctor_reply"):
        raise FeatureDisabled("Shifokor javobi hozircha oʻchirilgan.")

    patient = _get_patient(patient_id)

    text = (text or "").strip()
    if not text:
        raise ValidationError("Xabar matni boʻsh boʻlmasligi kerak.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValidationError("Xabar juda uzun.")

    if doctor_id is None:
        doctor_id = patient["doctor_id"]

    message_id = message_repo.create(
        patient_id, "doctor", text,
        meta_json=json.dumps({"doctor_id": doctor_id}, ensure_ascii=False),
    )

    events.emit(
        events.DOCTOR_REPLIED,
        patient_id=patient_id,
        doctor_id=doctor_id,
        message_id=message_id,
    )

    return {"message": _as_dict(message_repo.get(message_id))}


def get_trend(patient_id):
    """risk_score over time — the series behind the trend chart."""
    _get_patient(patient_id)
    points = [_as_dict(r) for r in assessment_repo.trend_for_patient(patient_id)]
    scores = [p["risk_score"] for p in points]
    return {
        "points": points,
        "max_score": max(scores) if scores else 0,
        "current": scores[-1] if scores else 0,
    }


def resolve_alert(alert_id):
    """Close an alert and announce it."""
    alert = alert_repo.get(alert_id)
    if alert is None:
        raise NotFound("Signal topilmadi.")
    if alert["status"] == "resolved":
        raise ValidationError("Signal allaqachon yopilgan.")

    alert_repo.resolve(alert_id)
    events.emit(events.ALERT_RESOLVED, alert_id=alert_id,
                patient_id=alert["patient_id"])
    return _as_dict(alert_repo.get(alert_id))
