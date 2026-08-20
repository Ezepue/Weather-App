"""Advice assembly. Importing this module registers every scorer."""

from __future__ import annotations

from ..domain.models import Advice
from ..meteorology import timeline
from . import activities  # importing this module is what registers the scorers
from .comfort import comfort
from .guidance import outfit, summary, sunscreen, umbrella
from .registry import all_scorers, score_all
from .snapshot import Snapshot

__all__ = ["Snapshot", "activities", "all_scorers", "build", "score_all"]


def build(report) -> Advice:
    snapshot = Snapshot.from_report(report)
    scored = score_all(snapshot)
    umbrella_advice = umbrella(snapshot)
    first_day = report.daily[0] if report.daily else None

    return Advice(
        comfort=comfort(snapshot),
        pressure_trend={},
        activities=scored,
        best_activity=max(scored, key=lambda a: a["score"]),
        umbrella=umbrella_advice,
        sunscreen=sunscreen(snapshot),
        outfit=outfit(snapshot),
        frost=snapshot.frost or {},
        rain_windows=timeline.rain_windows(snapshot.hourly, snapshot.now_epoch),
        dry_windows=timeline.dry_windows(snapshot.hourly, snapshot.now_epoch),
        air_out=timeline.air_out_window(snapshot.hourly, snapshot.now_epoch),
        extremes=timeline.extremes(snapshot.hourly, snapshot.now_epoch),
        precip_next_24h_mm=snapshot.next_24h_precip_mm,
        uv_max_today=round(snapshot.uv_max_today, 1),
        summary=summary(report.place.name, report.current, first_day, umbrella_advice),
    )
