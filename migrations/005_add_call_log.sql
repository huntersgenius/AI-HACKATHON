-- 005_add_call_log.sql — auto-call feature (notifiers/call_notifier.py).
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE call_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id         INTEGER NOT NULL REFERENCES patients(id),
    doctor_id          INTEGER REFERENCES doctors(id),
    alert_id           INTEGER REFERENCES alerts(id),
    provider           TEXT    DEFAULT 'smartcall',
    external_call_id   TEXT,                      -- call_id returned by the provider
    phone              TEXT    NOT NULL,
    trigger            TEXT    DEFAULT 'manual',   -- 'manual' | 'auto_red_alert'
    status             TEXT    DEFAULT 'queued',   -- 'queued'|'pending'|'sended'|'failed'|'cancelled'
    answered           INTEGER,                    -- 0/1, filled in once the provider reports it
    duration_seconds   INTEGER,
    pressed_one        INTEGER,                    -- 0/1 — patient pressed "1" during the call
    error_code         TEXT,
    created_at         TEXT    DEFAULT (datetime('now')),
    updated_at         TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX idx_call_log_patient ON call_log(patient_id, created_at);
CREATE INDEX idx_call_log_status  ON call_log(status);
