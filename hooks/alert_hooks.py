"""Raise a doctor-facing alert when an assessment comes back risky.

Subscribes to `assessment.created`, so neither the analyzer pipeline nor the
message service knows alerts exist. Deleting this file removes alerting and
breaks nothing else.
"""

import json

from core import events
from repos import alert_repo, assessment_repo, patient_repo

# Risk levels that deserve a doctor's attention.
ALERTING_LEVELS = ("yellow", "red")

SEVERITY_LABEL = {
    "yellow": "Eʼtibor talab qiladi",
    "red": "Shoshilinch",
}


def _signals_text(raw):
    """Turn the stored JSON array into a short Uzbek phrase."""
    try:
        signals = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return ""
    if not isinstance(signals, list):
        return ""
    readable = [str(s).replace("_", " ") for s in signals if str(s).strip()]
    return ", ".join(readable[:3])


def build_title(patient, assessment):
    """Alert headline the doctor sees in the list."""
    label = SEVERITY_LABEL.get(assessment["risk_level"], "Eʼtibor talab qiladi")
    signals = _signals_text(assessment["danger_signals"])
    day = assessment["checkin_id"] and patient["current_day"]
    parts = ["%s: %s" % (patient["full_name"], label.lower())]
    if signals:
        parts.append("(%s)" % signals)
    if day:
        parts.append("— %s-kun" % day)
    return " ".join(parts)


@events.on(events.ASSESSMENT_CREATED)
def raise_alert(patient_id, assessment_id, risk_level, **_ignored):
    if risk_level not in ALERTING_LEVELS:
        return

    patient = patient_repo.get(patient_id)
    assessment = assessment_repo.get(assessment_id)
    if patient is None or assessment is None:
        return

    alert_id = alert_repo.create(
        patient_id=patient_id,
        doctor_id=patient["doctor_id"],
        title=build_title(patient, assessment),
        severity=risk_level,
        assessment_id=assessment_id,
    )

    events.emit(
        events.ALERT_RAISED,
        patient_id=patient_id,
        alert_id=alert_id,
        severity=risk_level,
    )
