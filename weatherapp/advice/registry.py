"""Strategy registry for activity scorers.

A scorer is any callable taking a Snapshot and returning a score dict. They
register themselves at import time, so the orchestrator never enumerates them
by hand and adding one is a purely additive change.
"""

from __future__ import annotations

from typing import Callable

_BANDS = (
    (82, "Excellent", "ok"),
    (64, "Good", "ok"),
    (45, "Fair", "warn"),
    (25, "Poor", "bad"),
    (-1, "Forget it", "bad"),
)

_SCORERS: dict[str, Callable] = {}


def band_for(score: float) -> tuple[str, str]:
    for floor, label, tone in _BANDS:
        if score >= floor:
            return label, tone
    return "Forget it", "bad"


def verdict(key: str, label: str, icon: str, score: float, reasons: list, **extra) -> dict:
    score = max(0.0, min(100.0, score))
    band, tone = band_for(score)
    reasons = [r for r in reasons if r]
    return {
        "key": key,
        "label": label,
        "icon": icon,
        "score": round(score),
        "band": band,
        "tone": tone,
        "reason": reasons[0] if reasons else "Nothing working against it",
        "reasons": reasons[:3],
        **extra,
    }


def scorer(key: str, label: str, icon: str):
    """Register a scorer. Wrapped so each one only returns reasons and a score."""

    def decorate(fn):
        def run(snapshot) -> dict:
            score, reasons, extra = fn(snapshot)
            return verdict(key, label, icon, score, reasons, **extra)

        run.key = key
        run.label = label
        run.icon = icon
        run.__name__ = fn.__name__
        run.__doc__ = fn.__doc__
        _SCORERS[key] = run
        return run

    return decorate


def all_scorers() -> list:
    return list(_SCORERS.values())


def score_all(snapshot) -> list:
    return [run(snapshot) for run in _SCORERS.values()]


def get(key: str):
    return _SCORERS.get(key)
