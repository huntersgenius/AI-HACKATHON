"""The analyzer pipeline: run every registered analyzer, merge, persist.

Merging takes the highest risk any analyzer reported (red > yellow > green),
unions the danger signals, and keeps each analyzer's own verdict in
`analyzer_results` so a later analyzer never rewrites history.

A failing analyzer is logged and skipped — the pipeline still produces an
assessment as long as one analyzer answered.
"""

import json

from analyzers import base as analyzer_base
from core import events
from core.errors import NotFound
from repos import (assessment_repo, checkin_repo, message_repo, patient_repo)


def _log_exception(message, *args):
    from flask import current_app
    try:
        current_app.logger.exception(message, *args)
    except RuntimeError:
        pass


def build_context(patient, message, checkin=None):
    """Everything an analyzer may look at, as plain data."""
    template = None
    if checkin is not None and checkin["template_id"] is not None:
        template = checkin_repo.get_template(checkin["template_id"])

    return {
        "patient_id": patient["id"],
        "persona_key": patient["persona_key"],
        "diagnosis": patient["diagnosis"],
        "day_number": checkin["day_number"] if checkin is not None else patient["current_day"],
        "text": message["text"],
        "question_key": template["question_key"] if template is not None else None,
        "question_text": template["question_text"] if template is not None else None,
        "answer_type": template["answer_type"] if template is not None else None,
    }


def run_analyzers(context):
    """Run the registry; return {name: AnalyzerResult} for those that spoke."""
    results = {}
    for name, fn in analyzer_base.registered():
        try:
            result = fn(context)
        except Exception:
            _log_exception("analyzer failed: %s", name)
            continue
        if result is not None:
            results[name] = result
    return results


def merge(results):
    """Highest risk wins; signals are unioned; reasons are kept in order."""
    levels = [r.risk_level for r in results.values()]
    level = analyzer_base.max_risk(levels)

    signals = []
    for result in results.values():
        for signal in result.danger_signals:
            if signal not in signals:
                signals.append(signal)

    # The reasoning and action come from the analyzers that reached the
    # winning level, so a green voice never softens a red verdict.
    deciding = [r for r in results.values() if r.risk_level == level]
    reasoning = " ".join(r.reasoning for r in deciding if r.reasoning).strip()
    action = next((r.recommended_action for r in deciding
                   if r.recommended_action), None)
    score = max((r.risk_score for r in deciding), default=0)

    if len(results) > 1:
        source = "merged"
    elif results:
        source = next(iter(results))
    else:
        source = "rules"

    return {
        "risk_level": level,
        "risk_score": score,
        "danger_signals": signals,
        "reasoning": reasoning,
        "recommended_action": action,
        "source": source,
    }


def analyze_message(patient_id, message_id, checkin_id=None):
    """Analyze one patient answer and store the assessment."""
    patient = patient_repo.get(patient_id)
    if patient is None:
        raise NotFound("Bemor topilmadi.")

    message = message_repo.get(message_id)
    if message is None:
        raise NotFound("Xabar topilmadi.")

    checkin = checkin_repo.get(checkin_id) if checkin_id else None

    context = build_context(patient, message, checkin)
    results = run_analyzers(context)
    if not results:
        return None

    merged = merge(results)

    assessment_id = assessment_repo.create(
        patient_id=patient_id,
        risk_level=merged["risk_level"],
        risk_score=merged["risk_score"],
        checkin_id=checkin_id,
        message_id=message_id,
        danger_signals=json.dumps(merged["danger_signals"], ensure_ascii=False),
        reasoning=merged["reasoning"],
        recommended_action=merged["recommended_action"],
        analyzer_results=json.dumps(
            {name: r.as_dict() for name, r in results.items()},
            ensure_ascii=False),
        source=merged["source"],
    )

    patient_repo.set_risk_level(patient_id, merged["risk_level"])

    events.emit(
        events.ASSESSMENT_CREATED,
        patient_id=patient_id,
        assessment_id=assessment_id,
        risk_level=merged["risk_level"],
    )

    merged["assessment_id"] = assessment_id
    return merged
