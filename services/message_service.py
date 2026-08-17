"""Receiving patient answers and reading the conversation.

An answer is stored, tied to the check-in it responds to, and announced with
`checkin.answered`. Risk analysis is not called from here — it subscribes to
that event (phase 4), so this service does not grow when analysis arrives.
"""

import json

from core import events
from core.errors import NotFound, ValidationError
from repos import checkin_repo, message_repo, patient_repo

MAX_TEXT_LENGTH = 2000


def _get_patient(patient_id):
    patient = patient_repo.get(patient_id)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


def _clean_text(raw):
    text = (raw or "").strip()
    if not text:
        raise ValidationError("Xabar matni bo'sh bo'lmasligi kerak.")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationError("Xabar juda uzun.")
    return text


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def list_messages(patient_id, after_id=0, limit=200):
    """Messages newer than `after_id` — the incremental polling feed."""
    _get_patient(patient_id)
    rows = message_repo.list_after(patient_id, after_id=after_id, limit=limit)
    return [_as_dict(r) for r in rows]


def get_status(patient_id):
    """Current day, risk level and the question still awaiting an answer."""
    patient = _get_patient(patient_id)
    pending = checkin_repo.oldest_pending(patient_id)

    pending_question = None
    if pending is not None:
        pending_question = {
            "checkin_id": pending["id"],
            "day_number": pending["day_number"],
            "question_key": pending["question_key"],
            "question_text": pending["question_text"],
            "answer_type": pending["answer_type"],
            "config": _parse_json(pending["config_json"], {}),
        }

    return {
        "patient_id": patient["id"],
        "full_name": patient["full_name"],
        "current_day": patient["current_day"],
        "risk_level": patient["risk_level"],
        "last_message_id": message_repo.last_id(patient_id),
        "pending_question": pending_question,
    }


def _parse_json(raw, fallback):
    try:
        parsed = json.loads(raw or "")
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def receive_patient_message(patient_id, text):
    """Store a patient answer against the open check-in and announce it."""
    _get_patient(patient_id)
    text = _clean_text(text)

    pending = checkin_repo.oldest_pending(patient_id)
    checkin_id = pending["id"] if pending is not None else None

    message_id = message_repo.create(
        patient_id, "patient", text, checkin_id=checkin_id)

    if checkin_id is not None:
        checkin_repo.mark_answered(checkin_id)
        events.emit(
            events.CHECKIN_ANSWERED,
            patient_id=patient_id,
            checkin_id=checkin_id,
            message_id=message_id,
        )

    return {
        "message": _as_dict(message_repo.get(message_id)),
        "checkin_id": checkin_id,
    }
