"""Analyzer registry and result type (PLAN.md section 4.1).

A new risk rule is a new file in `analyzers/` carrying the `@analyzer`
decorator. The pipeline discovers it through REGISTRY — no existing file
changes.

An analyzer receives a context dict and returns an AnalyzerResult (or None
when it has nothing to say about this answer).
"""

from dataclasses import dataclass, field

# Risk ordering used everywhere: higher wins a merge.
RISK_ORDER = {"green": 0, "yellow": 1, "red": 2}

GREEN = "green"
YELLOW = "yellow"
RED = "red"


@dataclass
class AnalyzerResult:
    risk_level: str                      # 'green'|'yellow'|'red'
    risk_score: int                      # 0..100
    danger_signals: list = field(default_factory=list)
    reasoning: str = ""
    recommended_action: str = None

    def as_dict(self):
        return {
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "danger_signals": list(self.danger_signals),
            "reasoning": self.reasoning,
            "recommended_action": self.recommended_action,
        }


# name -> (priority, fn). Lower priority runs first.
REGISTRY = {}


def analyzer(name, priority=100):
    """Decorator: register a new analyzer under `name`."""

    def wrap(fn):
        REGISTRY[name] = (priority, fn)
        return fn

    return wrap


def registered():
    """Analyzers in run order, as (name, fn) pairs."""
    items = sorted(REGISTRY.items(), key=lambda kv: (kv[1][0], kv[0]))
    return [(name, fn) for name, (_priority, fn) in items]


def max_risk(levels):
    """Highest risk level of the given ones; 'green' when empty."""
    best = GREEN
    for level in levels:
        if RISK_ORDER.get(level, 0) > RISK_ORDER.get(best, 0):
            best = level
    return best
