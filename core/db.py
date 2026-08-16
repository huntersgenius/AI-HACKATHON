"""SQLite access primitives: connections, migrations, query helpers.

This module is infrastructure. Business SQL belongs in `repos/` — repos call
the helpers here, nothing else opens a connection by hand.
"""

import os
import sqlite3

from flask import current_app, g

_DB_KEY = "_hamroh_db"


def connect(db_path):
    """Open a configured connection. Callers are responsible for closing it."""
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db():
    """Request-scoped connection, created on first use and closed by teardown."""
    conn = getattr(g, _DB_KEY, None)
    if conn is None:
        conn = connect(current_app.config["DB_PATH"])
        setattr(g, _DB_KEY, conn)
    return conn


def close_db(_exc=None):
    conn = getattr(g, _DB_KEY, None)
    if conn is not None:
        setattr(g, _DB_KEY, None)
        conn.close()


# --- query helpers -------------------------------------------------------

def query_all(sql, params=()):
    """Return every row as a list of sqlite3.Row."""
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    """Return the first row, or None."""
    return get_db().execute(sql, params).fetchone()


def query_value(sql, params=(), default=None):
    """Return the first column of the first row, or `default`."""
    row = query_one(sql, params)
    if row is None:
        return default
    return row[0]


def execute(sql, params=()):
    """Run a write statement and return `lastrowid`."""
    cur = get_db().execute(sql, params)
    return cur.lastrowid


def execute_many(sql, seq_of_params):
    """Run a write statement for every parameter tuple; returns rowcount."""
    cur = get_db().executemany(sql, seq_of_params)
    return cur.rowcount


def executescript(script):
    """Run a multi-statement SQL script."""
    get_db().executescript(script)


# --- migrations ----------------------------------------------------------

_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);
"""


def _migration_files(migrations_dir):
    if not os.path.isdir(migrations_dir):
        return []
    names = [n for n in os.listdir(migrations_dir) if n.endswith(".sql")]
    return sorted(names)


def run_migrations(db_path, migrations_dir, logger=None):
    """Apply every migration file that is not yet in `schema_migrations`.

    Files run in filename order and each one runs in its own transaction, so a
    broken migration never leaves half of itself behind. Applied files are
    never re-run and must never be edited — new change, new numbered file.
    """
    applied = []
    conn = connect(db_path)
    try:
        conn.executescript(_MIGRATIONS_TABLE)
        done = {r["filename"] for r in conn.execute(
            "SELECT filename FROM schema_migrations")}

        for filename in _migration_files(migrations_dir):
            if filename in done:
                continue
            path = os.path.join(migrations_dir, filename)
            with open(path, "r", encoding="utf-8") as fh:
                sql = fh.read()
            # The transaction lives inside the script: sqlite3.executescript()
            # commits any transaction opened outside of it, so BEGIN/COMMIT
            # have to travel with the statements they wrap.
            escaped = filename.replace("'", "''")
            script = (
                "BEGIN;\n"
                + sql
                + "\nINSERT INTO schema_migrations (filename) VALUES "
                + "('" + escaped + "');\nCOMMIT;\n"
            )
            try:
                conn.executescript(script)
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                if logger:
                    logger.exception("migration failed: %s", filename)
                raise
            applied.append(filename)
            if logger:
                logger.info("migration applied: %s", filename)
    finally:
        conn.close()
    return applied


def init_app(app):
    app.teardown_appcontext(close_db)
    run_migrations(
        app.config["DB_PATH"],
        app.config["MIGRATIONS_DIR"],
        logger=app.logger,
    )
