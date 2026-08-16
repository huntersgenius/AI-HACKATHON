"""Run risk analysis when a patient answers.

This is why `message_service` never imports an analyzer: the reaction lives
here, and removing this file removes the behaviour cleanly.
"""

from core import events
from services import assessment_service


@events.on(events.CHECKIN_ANSWERED)
def analyze_answer(patient_id, message_id, checkin_id=None, **_ignored):
    assessment_service.analyze_message(
        patient_id, message_id, checkin_id=checkin_id)
