"""Auto-call + push notifications.

The SmartCall HTTP layer is monkeypatched everywhere here — these tests must
never place a real phone call. `test_smoke.py` already proves the flag stays
off by default; these confirm the *logic* around it.
"""

from config import Config
from tests.test_smoke import app, client  # noqa: F401  (fixture reuse)
from tests.test_smoke import advance, data, error, send


def test_call_notifier_disabled_by_default(client):
    resp = client.post("/api/v1/patients/1/calls", json={})
    assert error(resp)["code"] == "feature_disabled"


def test_call_notifier_not_configured_is_a_clean_failure(client, monkeypatch):
    """Flag on, but no groupID — must fail gracefully, no network call."""
    from notifiers import call_notifier

    monkeypatch.setattr(Config, "FEATURES", {**Config.FEATURES, "call_notifier": True})
    import config
    monkeypatch.setattr(config.features, "_flags",
                         {**config.features._flags, "call_notifier": True})
    monkeypatch.setattr(Config, "SMARTCALL_GROUP_ID", "")

    called = {"n": 0}

    def fail_if_called(*a, **k):
        called["n"] += 1
        raise AssertionError("must not hit the network when not configured")

    monkeypatch.setattr(call_notifier.requests, "post", fail_if_called)

    resp = client.post("/api/v1/patients/1/calls", json={})
    body = error(resp)
    assert body["code"] == "not_configured"
    assert called["n"] == 0


def test_call_placed_and_logged_with_mocked_provider(client, monkeypatch):
    from notifiers import call_notifier

    import config
    monkeypatch.setattr(config.features, "_flags",
                         {**config.features._flags, "call_notifier": True})
    monkeypatch.setattr(Config, "SMARTCALL_API_KEY", "test-key")
    monkeypatch.setattr(Config, "SMARTCALL_GROUP_ID", "1")

    class FakeResponse:
        def json(self):
            return {"status": "success", "call_id": 999, "limit": 100}

    monkeypatch.setattr(call_notifier.requests, "post",
                         lambda *a, **k: FakeResponse())

    resp = data(client.post("/api/v1/patients/1/calls", json={"doctor_id": 1}))
    assert resp["call"]["status"] == "pending"
    assert resp["call"]["external_call_id"] == "999"

    calls = data(client.get("/api/v1/patients/1/calls"))["calls"]
    assert len(calls) == 1


def test_auto_call_on_red_alert_uses_mocked_provider(client, monkeypatch):
    """A red alert should trigger call_hooks.py, which calls the mocked provider."""
    from notifiers import call_notifier

    import config
    monkeypatch.setattr(config.features, "_flags",
                         {**config.features._flags, "call_notifier": True})
    monkeypatch.setattr(Config, "SMARTCALL_API_KEY", "test-key")
    monkeypatch.setattr(Config, "SMARTCALL_GROUP_ID", "1")

    calls_made = []

    class FakeResponse:
        def json(self):
            return {"status": "success", "call_id": 555, "limit": 100}

    def fake_post(url, data=None, timeout=None):
        calls_made.append(data)
        return FakeResponse()

    monkeypatch.setattr(call_notifier.requests, "post", fake_post)

    advance(client, 1)
    send(client, 1, "Nafasimdan aseton hidi kelyapti, qustim")  # -> red

    # GET /calls opportunistically refreshes any still-"pending" row, which
    # is a second provider call by design (see call_service._refresh) — so
    # this checks the *create* call specifically, not the total count.
    log = data(client.get("/api/v1/patients/1/calls"))["calls"]
    assert len(log) == 1
    assert log[0]["trigger"] == "auto_red_alert"
    create_calls = [c for c in calls_made if "phone" in c]
    assert len(create_calls) == 1
    assert create_calls[0]["phone"] == "+998 90 111 22 33"


def test_push_subscribe_and_unsubscribe(client):
    sub = {
        "subscriber_type": "doctor",
        "subscriber_id": 1,
        "subscription": {
            "endpoint": "https://example.com/ep-test",
            "keys": {"p256dh": "abc", "auth": "def"},
        },
    }
    assert data(client.post("/api/v1/push/subscribe", json=sub))["subscribed"] is True
    assert data(client.post(
        "/api/v1/push/unsubscribe", json={"endpoint": "https://example.com/ep-test"}
    ))["subscribed"] is False


def test_push_subscribe_rejects_incomplete_payload(client):
    resp = client.post("/api/v1/push/subscribe", json={"subscriber_type": "doctor"})
    assert error(resp)["code"] == "validation_error"


def test_push_notifier_sends_on_alert_and_doctor_reply(client, monkeypatch):
    """push_hooks.py should call push_notifier.send_to_subscriber; mock it so
    no real Web Push (and no pywebpush network call) ever happens."""
    from notifiers import push_notifier

    sent = []
    monkeypatch.setattr(
        push_notifier, "send_to_subscriber",
        lambda *a, **k: sent.append((a, k)),
    )

    advance(client, 1)
    send(client, 1, "Nafasimdan aseton hidi kelyapti, qustim")  # -> red alert
    assert any(a[0] == "doctor" for a, k in sent)

    client.post("/api/v1/patients/1/doctor-message", json={"text": "Salom"})
    assert any(a[0] == "patient" for a, k in sent)
