"""Placing and tracking SmartCall voice-reminder calls.

A call is logged in `call_log` the moment it's requested (so the doctor sees
"queued" immediately), then handed to `notifiers/call_notifier.py`. Status
refreshes are pull-based: `list_calls` re-asks SmartCall for any row still
`pending`, which fits the same 3-second polling the rest of the app uses —
no background worker needed.
"""

from config import features
from core import events
from core.errors import AppError, FeatureDisabled, NotFound
from notifiers import call_notifier
from repos import call_repo, patient_repo

DUPLICATE_GUARD_SECONDS = 60


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def _get_patient(patient_id):
    patient = patient_repo.get(patient_id)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


def place_call(patient_id, doctor_id=None, alert_id=None, trigger="manual"):
    if not features.enabled("call_notifier"):
        raise FeatureDisabled("Avtomatik qoʻngʻiroq hozircha oʻchirilgan.")

    patient = _get_patient(patient_id)
    phone = (patient["phone_sim"] or "").strip()
    if not phone:
        raise AppError("Bemorning telefon raqami koʻrsatilmagan.",
                        code="no_phone", status=422)

    recent = call_repo.recent_call_for_phone(phone, DUPLICATE_GUARD_SECONDS)
    if recent is not None and recent["status"] in ("queued", "pending"):
        raise AppError(call_notifier.message_for("duplicate_call"),
                        code="duplicate_call", status=409)

    call_id = call_repo.create(
        patient_id, phone, doctor_id=doctor_id, alert_id=alert_id, trigger=trigger)

    result = call_notifier.place_call(phone)
    if not result["ok"]:
        call_repo.mark_failed(call_id, result.get("error_code", "unknown_error"))
        events.emit(events.CALL_FAILED, patient_id=patient_id, call_id=call_id,
                    error_code=result.get("error_code"))
        raise AppError(call_notifier.message_for(result.get("error_code")),
                        code=result.get("error_code", "call_failed"), status=502)

    call_repo.mark_queued(call_id, result.get("call_id"))
    events.emit(events.CALL_PLACED, patient_id=patient_id, call_id=call_id,
                trigger=trigger)
    return _as_dict(call_repo.get(call_id))


def _refresh(row):
    """Ask SmartCall for the latest status of one pending call."""
    result = call_notifier.check_status(row["external_call_id"])
    if not result["ok"]:
        return row

    raw = result.get("raw", {})
    status = raw.get("status", row["status"])
    call_repo.update_status(
        row["id"],
        status=status,
        answered=1 if raw.get("answer") else (0 if "answer" in raw else None),
        duration_seconds=raw.get("duration"),
        pressed_one=1 if raw.get("click") else (0 if "click" in raw else None),
    )
    return call_repo.get(row["id"])


def list_calls(patient_id):
    _get_patient(patient_id)
    rows = call_repo.list_for_patient(patient_id)
    refreshed = [
        _refresh(row) if row["status"] == "pending" and row["external_call_id"]
        else row
        for row in rows
    ]
    return [_as_dict(r) for r in refreshed]
