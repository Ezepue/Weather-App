"""The single input record every scorer receives.

Scorers take one uniform argument so they can be registered, listed and tested
without the registry knowing what any individual scorer looks at.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..meteorology import thermal, timeline


@dataclass(frozen=True, slots=True)
class Snapshot:
    temp_c: float
    humidity: float
    wind_kph: float
    precip_mm: float
    cloud: float
    uv: float
    feels_c: float
    now_epoch: int
    hourly: list
    gust_kph: float | None = None
    vis_km: float | None = None
    aqi_epa: int | None = None
    moon_illumination: float | None = None
    water_temp_c: float | None = None
    daylight_hours: float = 12.0
    next_24h_precip_mm: float = 0.0
    uv_max_today: float = 0.0
    chance_rain: int = 0
    golden_evening_epoch: int | None = None
    frost: dict | None = None

    @classmethod
    def from_report(cls, report) -> "Snapshot":
        current = report.current
        hourly = report.hourly or []
        first_day = report.daily[0] if report.daily else None
        air = report.air
        marine = report.marine
        astro = report.astro
        now = report.meta.now_epoch
        uv_max, _ = timeline.peak_uv(hourly, now)

        return cls(
            temp_c=current.temp_c,
            humidity=current.humidity,
            wind_kph=current.wind_kph,
            precip_mm=current.precip_mm or 0.0,
            cloud=current.cloud if current.cloud is not None else 50.0,
            uv=current.uv or 0.0,
            feels_c=current.feels_c,
            now_epoch=now,
            hourly=hourly,
            gust_kph=current.wind_gust_kph,
            vis_km=current.vis_km,
            aqi_epa=air.epa_index if air else None,
            moon_illumination=astro.moon_illumination if astro else None,
            water_temp_c=marine.water_temp_c if marine else None,
            daylight_hours=(astro.daylight_minutes or 720) / 60 if astro else 12.0,
            next_24h_precip_mm=timeline.total_precip(hourly, now),
            uv_max_today=max(uv_max, current.uv or 0.0),
            chance_rain=first_day.chance_rain if first_day else 0,
            golden_evening_epoch=astro.golden_evening_start_epoch if astro else None,
            frost=timeline.frost_risk(hourly),
        )

    def apparent(self, wind_kph: float | None = None) -> float:
        """Recompute felt temperature when a scorer cares about a different wind."""
        return thermal.feels_like(self.temp_c, self.humidity, wind_kph if wind_kph is not None else self.wind_kph)["value"]
