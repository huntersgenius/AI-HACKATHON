"""Loading prompt text from `prompts/*.txt`.

Prompt text never lives in Python. Files are read once and cached, and
placeholders use `string.Template` (`$name`) so JSON braces inside a prompt
need no escaping.
"""

import os
from string import Template

from flask import current_app

_cache = {}


def _prompts_dir():
    try:
        return current_app.config["PROMPTS_DIR"]
    except RuntimeError:  # no app context (tests, scripts)
        from config import Config
        return Config.PROMPTS_DIR


def load(name):
    """Return the raw text of `prompts/<name>`."""
    path = os.path.join(_prompts_dir(), name)
    cached = _cache.get(path)
    if cached is None:
        with open(path, "r", encoding="utf-8") as fh:
            cached = fh.read()
        _cache[path] = cached
    return cached


def render(name, **values):
    """Load a prompt and substitute `$placeholders`.

    Missing placeholders are left as-is rather than raising — a prompt edit
    should never take the demo down.
    """
    return Template(load(name)).safe_substitute(**values)


def clear_cache():
    _cache.clear()
