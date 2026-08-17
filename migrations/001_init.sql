-- 001_init.sql — initial schema (PLAN.md section 3.2).
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE doctors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL,
    clinic_name TEXT NOT NULL,
    phone_sim   TEXT
);

CREATE TABLE patients (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    persona_key    TEXT NOT NULL,
    diagnosis      TEXT,
    discharge_date TEXT,
    phone_sim      TEXT,
    doctor_id      INTEGER NOT NULL REFERENCES doctors(id),
    current_day    INTEGER DEFAULT 0,
    risk_level     TEXT    DEFAULT 'green',
    meta_json      TEXT    DEFAULT '{}',   -- extension: new field without a migration
    created_at     TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE checkin_templates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_key   TEXT NOT NULL,
    day_offset    INTEGER NOT NULL,
    seq           INTEGER DEFAULT 0,        -- order of several questions in one day
    question_key  TEXT NOT NULL,            -- 'temperature' | 'pain' | 'wound' ...
    question_text TEXT NOT NULL,
    answer_type   TEXT DEFAULT 'free_text', -- 'free_text'|'number'|'scale_1_10'|'yes_no'
    config_json   TEXT DEFAULT '{}'         -- min/max, unit, options
);

CREATE TABLE checkins (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id),
    template_id INTEGER REFERENCES checkin_templates(id),
    day_number  INTEGER NOT NULL,
    status      TEXT DEFAULT 'pending',     -- 'pending'|'answered'|'skipped'
    sent_at     TEXT DEFAULT (datetime('now')),
    answered_at TEXT
);

CREATE TABLE messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    checkin_id INTEGER REFERENCES checkins(id),
    sender     TEXT NOT NULL,               -- 'system'|'patient'|'doctor'
    text       TEXT NOT NULL,
    meta_json  TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE ai_assessments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id         INTEGER NOT NULL REFERENCES patients(id),
    checkin_id         INTEGER REFERENCES checkins(id),
    message_id         INTEGER REFERENCES messages(id),
    risk_level         TEXT NOT NULL,        -- 'green'|'yellow'|'red'
    risk_score         INTEGER DEFAULT 0,    -- 0..100, for the trend chart
    danger_signals     TEXT DEFAULT '[]',    -- JSON array
    reasoning          TEXT,
    recommended_action TEXT,
    analyzer_results   TEXT DEFAULT '{}',    -- what each analyzer said (debug + transparency)
    source             TEXT DEFAULT 'llm',   -- 'llm'|'rules'|'merged'
    created_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER NOT NULL REFERENCES patients(id),
    doctor_id     INTEGER NOT NULL REFERENCES doctors(id),
    assessment_id INTEGER REFERENCES ai_assessments(id),
    severity      TEXT DEFAULT 'yellow',
    title         TEXT NOT NULL,
    status        TEXT DEFAULT 'new',        -- 'new'|'seen'|'resolved'
    created_at    TEXT DEFAULT (datetime('now')),
    resolved_at   TEXT
);

CREATE TABLE event_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    payload    TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_messages_patient  ON messages(patient_id, created_at);
CREATE INDEX idx_assess_patient    ON ai_assessments(patient_id, created_at);
CREATE INDEX idx_alerts_doctor     ON alerts(doctor_id, status);
CREATE INDEX idx_templates_lookup  ON checkin_templates(persona_key, day_offset, seq);
