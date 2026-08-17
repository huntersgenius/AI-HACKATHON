"""SQL for the `push_subscriptions` table."""

from core import db


def upsert(subscriber_type, subscriber_id, endpoint, p256dh, auth):
    db.execute(
        """
        INSERT INTO push_subscriptions (subscriber_type, subscriber_id, endpoint, p256dh, auth)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(endpoint) DO UPDATE SET
            subscriber_type = excluded.subscriber_type,
            subscriber_id   = excluded.subscriber_id,
            p256dh          = excluded.p256dh,
            auth            = excluded.auth
        """,
        (subscriber_type, subscriber_id, endpoint, p256dh, auth),
    )


def delete(endpoint):
    db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def list_for(subscriber_type, subscriber_id):
    return db.query_all(
        """
        SELECT * FROM push_subscriptions
         WHERE subscriber_type = ? AND subscriber_id = ?
        """,
        (subscriber_type, subscriber_id),
    )
