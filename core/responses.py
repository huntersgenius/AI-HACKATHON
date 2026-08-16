"""The one API envelope (PLAN.md section 5).

    {"ok": true,  "data": ...}
    {"ok": false, "error": {"code": ..., "message": ...}}

Routes return `ok(...)`; failures come from raising `AppError`, which the
global handler converts with `fail(...)`. Never hand-build this shape.
"""

import sqlite3

from flask import jsonify


def _plain(value):
    """Make sqlite3.Row (and nested containers of it) JSON-serialisable."""
    if isinstance(value, sqlite3.Row):
        return {k: _plain(value[k]) for k in value.keys()}
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def ok(data=None, status=200):
    return jsonify({"ok": True, "data": _plain(data)}), status


def fail(code, message, status=400, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = _plain(details)
    return jsonify({"ok": False, "error": error}), status
