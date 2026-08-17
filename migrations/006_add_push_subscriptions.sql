-- 006_add_push_subscriptions.sql — Web Push (notifiers/push_notifier.py).
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE push_subscriptions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_type  TEXT    NOT NULL,   -- 'patient' | 'doctor'
    subscriber_id    INTEGER NOT NULL,
    endpoint         TEXT    NOT NULL UNIQUE,
    p256dh           TEXT    NOT NULL,
    auth             TEXT    NOT NULL,
    created_at       TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX idx_push_subscriber ON push_subscriptions(subscriber_type, subscriber_id);
