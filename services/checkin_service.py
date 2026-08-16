"""Sending daily check-in questions.

The follow-up plan lives entirely in `checkin_templates`: this service asks the
repo for "the questions of persona X on day N" and sends whatever comes back.
A new persona, a new day or a new question is therefore a migration row — this
file never learns any persona's name.
"""

import json

from config import features
from core import events
from core.errors import AppError, NotFound
from repos import checkin_repo, message_repo, patient_repo


class PlanFinished(AppError):
    code = "plan_finished"
    status = 409
    message = "Bu bemor uchun kuzatuv rejasi yakunlangan."


class NoQuestionsForDay(AppError):
    code = "no_questions_for_day"
    status = 404
    message = "Bu kun uchun savol topilmadi."


def _question_meta(template):
    """Message metadata the chat UI needs to render the right answer widget."""
    return {
        "question_key": template["question_key"],
        "answer_type": template["answer_type"],
        "config": _parse_config(template["config_json"]),
    }


def _parse_config(raw):
    """config_json is author-written data — a bad row must not break a send."""
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def get_patient(patient_id):
    patient = patient_repo.get(patient_id)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


def send_day(patient_id, day_number):
    """Send every question configured for `day_number`; return what was sent."""
    patient = get_patient(patient_id)
    persona_key = patient["persona_key"]

    templates = checkin_repo.templates_for_day(persona_key, day_number)
    if not templates:
        raise NoQuestionsForDay()

    # Until multi_question is switched on, only the first question of a day
    # goes out — the extra rows stay in the data, unsent.
    if not features.enabled("multi_question"):
        templates = templates[:1]

    sent = []
    for template in templates:
        meta = _question_meta(template)
        checkin_id = checkin_repo.create(patient_id, template["id"], day_number)
        message_id = message_repo.create(
            patient_id,
            "system",
            template["question_text"],
            checkin_id=checkin_id,
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
        events.emit(
            events.CHECKIN_SENT,
            patient_id=patient_id,
            checkin_id=checkin_id,
            day_number=day_number,
        )
        sent.append({
            "checkin_id": checkin_id,
            "message_id": message_id,
            "question_key": meta["question_key"],
            "question_text": template["question_text"],
            "answer_type": meta["answer_type"],
            "config": meta["config"],
        })

    patient_repo.set_current_day(patient_id, day_number)
    return sent


def advance_day(patient_id):
    """Move the patient one day forward and send that day's check-in."""
    patient = get_patient(patient_id)
    persona_key = patient["persona_key"]

    next_day = (patient["current_day"] or 0) + 1
    last_day = checkin_repo.max_day_offset(persona_key)
    if last_day and next_day > last_day:
        raise PlanFinished()

    if checkin_repo.exists_for_day(patient_id, next_day):
        raise AppError(
            "Bu kun uchun savol allaqachon yuborilgan.",
            code="day_already_sent",
            status=409,
        )

    questions = send_day(patient_id, next_day)
    return {
        "patient_id": patient_id,
        "day_number": next_day,
        "last_day": last_day,
        "is_last_day": bool(last_day) and next_day >= last_day,
        "questions": questions,
    }
