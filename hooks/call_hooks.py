"""Place an automatic reminder call when a red alert is raised.

Subscribes to `alert.raised` — neither the analyzer pipeline nor
`alert_hooks.py` knows this exists. Deleting this file removes auto-calling
and breaks nothing else. Gated by the `call_notifier` feature flag (off by
default, see config.py) so this never fires against the seeded demo phone
numbers unless someone deliberately turns it on with a real SmartCall
account.
"""

from config import features
from core import events
from repos import patient_repo
from services import call_service

AUTO_CALL_SEVERITIES = ("red",)


@events.on(events.ALERT_RAISED)
def call_on_red_alert(patient_id, alert_id, severity, **_ignored):
    if not features.enabled("call_notifier"):
        return
    if severity not in AUTO_CALL_SEVERITIES:
        return

    patient = patient_repo.get(patient_id)
    if patient is None:
        return

    try:
        call_service.place_call(
            patient_id,
            doctor_id=patient["doctor_id"],
            alert_id=alert_id,
            trigger="auto_red_alert",
        )
    except Exception:
        # duplicate_call / not_configured / network errors are expected here;
        # events.emit() already isolates hook failures, but call_service can
        # also raise AppError directly — never let that break the alert flow.
        pass
