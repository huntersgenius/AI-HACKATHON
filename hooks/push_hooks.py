"""Web Push reactions: notify a doctor when an alert fires, notify a patient
when the doctor replies. Subscribes to the same events `alert_hooks.py` and
`message_service`/`doctor_service` already emit — deleting this file removes
push notifications and breaks nothing else.
"""

from core import events
from notifiers import push_notifier
from repos import alert_repo, message_repo, patient_repo


@events.on(events.ALERT_RAISED)
def push_alert_to_doctor(patient_id, alert_id, severity, **_ignored):
    alert = alert_repo.get(alert_id)
    if alert is None:
        return
    push_notifier.send_to_subscriber(
        "doctor", alert["doctor_id"],
        title="Yangi signal" if severity == "yellow" else "Shoshilinch signal",
        body=alert["title"],
        url="/doctor/patient/%d" % patient_id,
    )


@events.on(events.DOCTOR_REPLIED)
def push_reply_to_patient(patient_id, doctor_id, message_id, **_ignored):
    message = message_repo.get(message_id)
    patient = patient_repo.get(patient_id)
    if message is None or patient is None:
        return
    push_notifier.send_to_subscriber(
        "patient", patient_id,
        title="Shifokordan xabar",
        body=message["text"],
        url="/patient/%d/chat" % patient_id,
    )
