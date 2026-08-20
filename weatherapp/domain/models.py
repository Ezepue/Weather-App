"""The wire format, defined once.

Providers build these; the API serialises them; the front end reads them. A
field that is not here does not exist anywhere else in the system.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


def _clean(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _clean(asdict(value))
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, float):
        # JSON has no float repr guarantees; round once, at the boundary.
        return round(value, 4)
    return value


@dataclass(frozen=True, slots=True)
class Condition:
    slug: str
    text: str
    family: str
    wet: bool
    is_day: bool
    code: int | None = None


@dataclass(frozen=True, slots=True)
class PlaceRef:
    name: str
    country: str
    lat: float
    lon: float
    tz_id: str
    utc_offset_hours: float
    localtime_epoch: int
    localtime_iso: str
    region: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class Observation:
    observed_epoch: int
    is_day: bool
    condition: Condition
    temp_c: float
    feels_c: float
    feels_basis: str
    humidity: float
    dewpoint_c: float
    pressure_mb: float
    wind_kph: float
    wind_dir_deg: float
    wind_dir_16: str
    beaufort_force: int | None
    beaufort_name: str
    cloud: float
    uv: float
    precip_mm: float
    vis_km: float | None = None
    wind_gust_kph: float | None = None
    snow_cm: float = 0.0
    heat_index_c: float | None = None
    wind_chill_c: float | None = None
    humidex_c: float | None = None
    # Filled by the service, not by providers: presentation-ready derivations.
    barb: dict | None = None
    uv_band: dict | None = None


@dataclass(frozen=True, slots=True)
class HourPoint:
    t: int
    temp_c: float
    feels_c: float
    dewpoint_c: float
    humidity: float
    precip_mm: float
    chance_rain: int
    chance_snow: int
    wind_kph: float
    wind_dir_deg: float
    pressure_mb: float
    cloud: float
    uv: float
    is_day: bool
    condition: Condition
    gust_kph: float | None = None
    vis_km: float | None = None


@dataclass(frozen=True, slots=True)
class DayPoint:
    date: str
    date_epoch: int
    condition: Condition
    maxtemp_c: float
    mintemp_c: float
    avgtemp_c: float
    maxwind_kph: float
    totalprecip_mm: float
    avghumidity: float
    chance_rain: int
    chance_snow: int
    uv: float
    totalsnow_cm: float = 0.0
    sunrise_epoch: int | None = None
    sunset_epoch: int | None = None
    moonrise_epoch: int | None = None
    moonset_epoch: int | None = None
    moon_phase: str = ""
    moon_illumination: float | None = None
    daylight_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class AirQuality:
    pollutants: dict
    sub_indices: dict
    aqi_us: int | None
    dominant: str | None
    category: dict
    basis: str
    epa_index: int | None = None
    defra_index: int | None = None
    defra_label: str | None = None


@dataclass(frozen=True, slots=True)
class Marine:
    wave_m: float | None
    wave_period_s: float | None
    swell_dir_deg: float | None
    water_temp_c: float | None
    hours: list = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Astro:
    sunrise_epoch: int | None
    sunset_epoch: int | None
    dawn_epoch: int | None
    dusk_epoch: int | None
    solar_noon_epoch: int | None
    golden_morning_end_epoch: int | None
    golden_evening_start_epoch: int | None
    daylight_minutes: int | None
    daylight_delta_minutes: float | None
    solar_elevation: float
    solar_azimuth: float
    moon_phase: str
    moon_illumination: float
    moon_age_days: float
    moon_waxing: bool
    sun_path: list = field(default_factory=list)
    moonrise_epoch: int | None = None
    moonset_epoch: int | None = None


@dataclass(frozen=True, slots=True)
class Alert:
    id: str
    event: str
    headline: str
    severity: str
    tone: str
    areas: str = ""
    effective_epoch: int | None = None
    expires_epoch: int | None = None
    description: str = ""
    instruction: str = ""


@dataclass(frozen=True, slots=True)
class Advice:
    """Everything the service derives from acquired data, interpretive or not."""

    comfort: dict
    pressure_trend: dict
    activities: list
    best_activity: dict
    umbrella: dict
    sunscreen: dict
    outfit: dict
    frost: dict
    rain_windows: list
    dry_windows: list
    air_out: dict | None
    extremes: dict
    precip_next_24h_mm: float
    uv_max_today: float
    summary: str


@dataclass(frozen=True, slots=True)
class Meta:
    provider: str
    version: str
    generated_epoch: int
    now_epoch: int
    forecast_days: int
    cached: bool = False
    age_seconds: float = 0.0
    stale: bool = False
    notices: list = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProviderBundle:
    """What a provider is responsible for: acquired data, nothing derived.

    Solar geometry and advice are computed once by the service rather than
    duplicated in every adapter.
    """

    place: PlaceRef
    current: Observation
    hourly: list
    daily: list
    air: AirQuality | None = None
    marine: Marine | None = None
    alerts: list = field(default_factory=list)
    notices: list = field(default_factory=list)
    cached: bool = False
    age_seconds: float = 0.0
    stale: bool = False


@dataclass(frozen=True, slots=True)
class Report:
    meta: Meta
    place: PlaceRef
    current: Observation
    hourly: list
    daily: list
    astro: Astro
    air: AirQuality | None = None
    marine: Marine | None = None
    alerts: list = field(default_factory=list)
    advice: Advice | None = None

    def to_dict(self) -> dict:
        return _clean(self)

    def with_meta(self, **changes) -> "Report":
        from dataclasses import replace
        return replace(self, meta=replace(self.meta, **changes))

    def with_advice(self, advice: Advice) -> "Report":
        from dataclasses import replace
        return replace(self, advice=advice)
