"""Assembles a Report from a provider bundle.

The order matters: solar geometry must exist before advice, because several
scorers read daylight length and moon illumination. Keeping that sequence in
one visible place is the reason this is a service and not a pile of helpers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .. import advice as advice_layer
from ..domain.models import Astro, Meta, Report
from ..meteorology import solar, thermal, timeline, wind


class ReportService:
    def __init__(self, provider, clock, settings):
        self._provider = provider
        self._clock = clock
        self._settings = settings

    def report(self, query: str, days: int | None = None) -> Report:
        days = days or self._settings.forecast_days
        bundle = self._provider.fetch(query or self._settings.default_place, days)
        report = self._assemble(bundle, days)
        return report.with_advice(self._advice(report))

    def search(self, query: str, limit: int = 8) -> list[dict]:
        return self._provider.search(query, limit)

    def compare(self, queries: list[str], days: int | None = None) -> list[Report]:
        return [self.report(query, days) for query in queries if (query or "").strip()]

    # ---- assembly -------------------------------------------------------

    def _now(self) -> int:
        """Bucketed wall clock.

        A report that changed every second would defeat ETags and force a full
        re-render on every poll, so 'now' advances in cache-sized steps.
        """
        now = self._clock.epoch()
        quantum = max(1, self._settings.time_quantum)
        return now - (now % quantum)

    def _notices(self, bundle) -> list:
        """Say why the data is synthetic when the reason is a fixable mistake."""
        notices = list(bundle.notices)
        if self._settings.key_status == "placeholder" and self._settings.key_note:
            notices.insert(0, self._settings.key_note)
        return notices

    def _assemble(self, bundle, days: int) -> Report:
        now = self._now()
        return Report(
            meta=Meta(
                provider=self._provider.name,
                version=self._settings.version,
                generated_epoch=now,
                now_epoch=now,
                forecast_days=days,
                cached=bundle.cached,
                age_seconds=bundle.age_seconds,
                stale=bundle.stale,
                notices=self._notices(bundle),
            ),
            place=bundle.place,
            current=self._enrich(bundle.current),
            hourly=bundle.hourly,
            daily=bundle.daily,
            astro=self._astro(bundle, now),
            air=bundle.air,
            marine=bundle.marine,
            alerts=bundle.alerts,
        )

    @staticmethod
    def _enrich(current):
        """Attach derivations the UI needs, so adapters stay translation-only."""
        from dataclasses import replace
        return replace(
            current,
            barb=wind.barb(current.wind_kph),
            uv_band=thermal.uv_band(current.uv),
        )

    def _astro(self, bundle, now_epoch: int) -> Astro:
        place = bundle.place
        zone = timezone(timedelta(hours=place.utc_offset_hours))
        local_noon = datetime.fromtimestamp(now_epoch, zone).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        events = solar.solar_events(local_noon, place.lat, place.lon)
        position = solar.sun_position(datetime.fromtimestamp(now_epoch, timezone.utc), place.lat, place.lon)
        moon = solar.moon_phase(datetime.fromtimestamp(now_epoch, timezone.utc))
        first_day = bundle.daily[0] if bundle.daily else None

        def stamp(key):
            value = events.get(key)
            return int(value.timestamp()) if value else None

        # Prefer the provider's own rise/set times when it supplies them; fall
        # back to computed geometry, which also covers the polar cases.
        sunrise = (first_day.sunrise_epoch if first_day else None) or stamp("sunrise")
        sunset = (first_day.sunset_epoch if first_day else None) or stamp("sunset")
        illumination = (first_day.moon_illumination if first_day else None)

        return Astro(
            sunrise_epoch=sunrise,
            sunset_epoch=sunset,
            dawn_epoch=stamp("dawn"),
            dusk_epoch=stamp("dusk"),
            solar_noon_epoch=stamp("solar_noon"),
            golden_morning_end_epoch=stamp("golden_morning_end"),
            golden_evening_start_epoch=stamp("golden_evening_start"),
            daylight_minutes=events.get("daylight_minutes"),
            daylight_delta_minutes=solar.daylight_delta(local_noon, place.lat, place.lon),
            solar_elevation=round(position.elevation, 2),
            solar_azimuth=round(position.azimuth, 2),
            moon_phase=(first_day.moon_phase if first_day and first_day.moon_phase else moon["name"]),
            moon_illumination=illumination if illumination is not None else moon["illumination"],
            moon_age_days=moon["age_days"],
            moon_waxing=moon["waxing"],
            sun_path=solar.sun_path(local_noon, place.lat, place.lon, samples=49),
            moonrise_epoch=first_day.moonrise_epoch if first_day else None,
            moonset_epoch=first_day.moonset_epoch if first_day else None,
        )

    def _advice(self, report: Report):
        from dataclasses import replace
        built = advice_layer.build(report)
        return replace(built, pressure_trend=timeline.pressure_trend(
            report.hourly, report.meta.now_epoch, report.current.pressure_mb
        ))
