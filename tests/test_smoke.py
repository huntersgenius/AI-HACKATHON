"""Smoke test for the demo chain (PLAN.md section 10, safety net 5).

advance-day → answer → assessment → alert → dashboard → doctor reply → resolve.
Every test runs against a throwaway database built from the real migrations,
so a broken migration fails here too.
"""

import os
import tempfile

import pytest

from app import create_app
from config import Config


@pytest.fixture()
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)  # let the migration runner create it

    class TestConfig(Config):
        DB_PATH = path
        DEBUG = False

    application = create_app(TestConfig)
    yield application

    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(path + suffix)
        except OSError:
            pass


@pytest.fixture()
def client(app):
    return app.test_client()


def data(response):
    """Unwrap the API envelope, asserting it is the success shape."""
    payload = response.get_json()
    assert payload["ok"] is True, payload
    return payload["data"]


def error(response):
    payload = response.get_json()
    assert payload["ok"] is False, payload
    return payload["error"]


# --- infrastructure ------------------------------------------------------

def test_health_returns_envelope(client):
    body = data(client.get("/health"))
    assert body["status"] == "ok"


def test_migrations_seeded_three_personas(client):
    patients = data(client.get("/api/v1/doctors/1/patients"))["patients"]
    assert {p["persona_key"] for p in patients} == {"bobur", "sardor", "nodira"}


def test_unknown_route_uses_error_envelope(client):
    assert error(client.get("/api/v1/nope"))["code"] == "not_found"


# --- the demo chain ------------------------------------------------------

def send(client, pid, text):
    return client.post("/api/v1/patients/%d/messages" % pid, json={"text": text})


def advance(client, pid):
    return client.post("/api/v1/demo/advance-day", json={"patient_id": pid})


def test_full_chain_red_answer_raises_alert(client):
    sent = data(advance(client, 1))
    assert sent["day_number"] == 1
    assert sent["questions"][0]["question_key"] == "glucose_fasting"

    # Ketoatsidoz: aseton hidi + qusish. Protokol bo'yicha qizil daraja.
    data(send(client, 1, "Ogzim quruq, nafasimdan galati hid kelyapti, qustim"))

    timeline = data(client.get("/api/v1/patients/1/timeline"))["items"]
    assessments = [i for i in timeline if i["kind"] == "assessment"]
    assert len(assessments) == 1
    assert assessments[0]["risk_level"] == "red"
    assert "aseton_hidi" in assessments[0]["danger_signals"]

    dashboard = data(client.get("/api/v1/doctors/1/dashboard"))
    assert dashboard["counts"]["red"] == 1
    assert dashboard["counts"]["new_alerts"] == 1
    assert dashboard["patients"][0]["full_name"] == "Bobur Aliyev"

    alerts = data(client.get("/api/v1/doctors/1/alerts?status=new"))["alerts"]
    assert alerts[0]["severity"] == "red"

    events = [e["event_name"] for e in
              data(client.get("/api/v1/demo/events"))["events"]]
    for name in ("checkin.sent", "checkin.answered",
                 "assessment.created", "alert.raised"):
        assert name in events, events


def test_green_answer_raises_no_alert(client):
    advance(client, 1)
    # Nahorgi qand 6.4 — maqsad < 7.0, ya'ni yashil.
    data(send(client, 1, "6.4"))
    assert data(client.get("/api/v1/doctors/1/dashboard"))["counts"]["new_alerts"] == 0


def test_hypoglycaemia_is_flagged_red(client):
    """Gipoglikemiya (< 3.9 mmol/l) — giperglikemiyadan teskari xavf."""
    advance(client, 1)
    data(send(client, 1, "3.2"))
    latest = data(client.get("/api/v1/patients/1/detail"))["latest_assessment"]
    assert latest["risk_level"] == "red"
    assert "gipoglikemiya" in latest["danger_signals"]


def test_incremental_polling_returns_only_new_messages(client):
    advance(client, 1)
    first = data(client.get("/api/v1/patients/1/messages?after_id=0"))["messages"]
    last_id = first[-1]["id"]
    data(send(client, 1, "6.4"))
    fresh = data(client.get("/api/v1/patients/1/messages?after_id=%d" % last_id))
    assert [m["sender"] for m in fresh["messages"]] == ["patient"]


def test_doctor_reply_reaches_patient_chat(client):
    advance(client, 1)
    data(client.post("/api/v1/patients/1/doctor-message",
                     json={"text": "Bugun qabulga keling."}))
    messages = data(client.get("/api/v1/patients/1/messages?after_id=0"))["messages"]
    assert messages[-1]["sender"] == "doctor"
    assert messages[-1]["text"] == "Bugun qabulga keling."


def test_alert_can_be_resolved_once(client):
    advance(client, 1)
    data(send(client, 1, "Nafasimdan aseton hidi kelyapti"))
    alert = data(client.get("/api/v1/doctors/1/alerts?status=new"))["alerts"][0]

    resolved = data(client.post("/api/v1/alerts/%d/resolve" % alert["id"]))["alert"]
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert data(client.get("/api/v1/doctors/1/alerts?status=new"))["alerts"] == []

    # Resolving twice is a validation error, not a crash.
    assert error(client.post("/api/v1/alerts/%d/resolve" % alert["id"]))[
        "code"] == "validation_error"


def test_trend_series_follows_the_answers(client):
    advance(client, 1)
    data(send(client, 1, "6.4"))            # yashil: maqsad ichida
    advance(client, 1)
    data(send(client, 1, "Nafasimdan aseton hidi kelyapti"))   # qizil

    trend = data(client.get("/api/v1/patients/1/trend"))
    assert [p["risk_level"] for p in trend["points"]] == ["green", "red"]
    assert trend["current"] == trend["points"][-1]["risk_score"]


def test_reset_restores_seeded_state(client):
    advance(client, 1)
    data(send(client, 1, "Nafasimdan aseton hidi kelyapti, qustim"))
    assert data(client.get("/api/v1/doctors/1/dashboard"))["counts"]["new_alerts"] == 1

    result = data(client.post("/api/v1/demo/reset"))
    assert all(p["current_day"] == 0 for p in result["patients"])

    dashboard = data(client.get("/api/v1/doctors/1/dashboard"))
    assert dashboard["counts"] == {"total": 3, "red": 0, "yellow": 0,
                                   "green": 3, "new_alerts": 0}
    assert data(client.get("/api/v1/patients/1/timeline"))["items"] == []
    # Seeded data survives a reset: the questions are still there.
    assert data(advance(client, 1))["questions"][0]["question_key"] == "glucose_fasting"


# --- personas are data, not code -----------------------------------------

@pytest.mark.parametrize("pid,expected_first_question", [
    (1, "glucose_fasting"),   # Bobur — 2-tur
    (2, "glucose_fasting"),   # Sardor — 1-tur
    (3, "glucose_fasting"),   # Nodira — gestatsion
])
def test_every_persona_runs_the_same_pipeline(client, pid, expected_first_question):
    sent = data(advance(client, pid))
    assert sent["questions"][0]["question_key"] == expected_first_question
    data(send(client, pid, "Nafasimdan aseton hidi kelyapti"))
    latest = data(client.get("/api/v1/patients/%d/detail" % pid))["latest_assessment"]
    assert latest["risk_level"] == "red"


# --- guard rails ---------------------------------------------------------

def test_plan_end_is_reported_not_crashed(client):
    for _ in range(5):
        advance(client, 1)
    assert error(advance(client, 1))["code"] == "plan_finished"


def test_blank_answer_is_rejected(client):
    advance(client, 1)
    assert error(send(client, 1, "   "))["code"] == "validation_error"


def test_unknown_patient_is_not_found(client):
    assert error(client.get("/api/v1/patients/999/timeline"))["code"] == "not_found"
