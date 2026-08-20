"""Adapter for weatherapi.com.

The upstream shape stops here. Nothing outside this file knows that WeatherAPI
nests hours inside days, reports condition codes as integers, or returns air
quality under a key with a hyphen in it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..domain.models import (
    AirQuality, Alert, Condition, DayPoint, HourPoint, Marine, Observation,
    PlaceRef, ProviderBundle,
)
from ..domain.protocols import ProviderError
from ..meteorology import air, conditions, thermal, wind
from .base import parse_latlon

_ALERT_TONES = {
    "extreme": "bad", "severe": "bad", "moderate": "warn", "minor": "warn",
}


def _epoch(value, offset_hours: float) -> int | None:
    """Upstream local timestamps carry no zone; the location's offset supplies it."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(str(value), fmt)
        except ValueError:
            continue
        zone = timezone(timedelta(hours=offset_hours))
        return int(naive.replace(tzinfo=zone).timestamp())
    return None


def _clock_epoch(day_epoch: int | None, clock_text: str, offset_hours: float) -> int | None:
    """Astronomy times arrive as '06:42 AM' with no date attached."""
    if not clock_text or day_epoch is None or "no " in clock_text.lower():
        return None
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            parsed = datetime.strptime(clock_text.strip(), fmt)
        except ValueError:
            continue
        zone = timezone(timedelta(hours=offset_hours))
        base = datetime.fromtimestamp(day_epoch, zone)
        return int(base.replace(hour=parsed.hour, minute=parsed.minute).timestamp())
    return None


class WeatherAPIProvider:
    name = "weatherapi"

    def __init__(self, http, api_key: str, base_url: str, marine_enabled: bool = True):
        if not api_key:
            raise ValueError("WeatherAPIProvider requires an API key")
        self._http = http
        self._key = api_key
        self._base = base_url.rstrip("/") + "/"
        self._marine_enabled = marine_enabled

    # ---- WeatherProvider ------------------------------------------------

    def search(self, query: str, limit: int = 8) -> list[dict]:
        if not (query or "").strip():
            return []
        rows = self._http.get_json(self._base + "search.json", {"key": self._key, "q": query})
        if not isinstance(rows, list):
            return []
        return [
            {
                "name": row.get("name", ""),
                "region": row.get("region", ""),
                "country": row.get("country", ""),
                "lat": row.get("lat"),
                "lon": row.get("lon"),
                "tz_id": "",
                "label": ", ".join(p for p in (row.get("name"), row.get("region"), row.get("country")) if p),
            }
            for row in rows[:limit]
        ]

    def fetch(self, query: str, days: int = 3) -> ProviderBundle:
        payload = self._http.get_json(
            self._base + "forecast.json",
            {"key": self._key, "q": query, "days": max(1, days), "aqi": "yes", "alerts": "yes"},
        )
        location = payload.get("location") or {}
        current = payload.get("current") or {}
        if not location or not current:
            raise ProviderError("Upstream returned no observation", 502, "upstream")

        offset = self._offset_hours(location)
        place = self._place(location, offset)
        hours = self._hours(payload, offset)
        daily = self._daily(payload, offset)
        notices: list[str] = []

        marine = None
        if self._marine_enabled:
            marine, marine_notice = self._marine(query, offset)
            if marine_notice:
                notices.append(marine_notice)

        return ProviderBundle(
            place=place,
            current=self._current(current, offset),
            hourly=hours,
            daily=daily,
            air=self._air(current.get("air_quality")),
            marine=marine,
            alerts=self._alerts(payload, offset),
            notices=notices,
        )

    # ---- translation ----------------------------------------------------

    @staticmethod
    def _offset_hours(location: dict) -> float:
        localtime_epoch = location.get("localtime_epoch")
        localtime = location.get("localtime")
        if localtime_epoch and localtime:
            try:
                naive = datetime.strptime(localtime, "%Y-%m-%d %H:%M")
            except ValueError:
                return 0.0
            utc = datetime.fromtimestamp(localtime_epoch, timezone.utc).replace(tzinfo=None)
            return round((naive - utc).total_seconds() / 900) * 0.25
        return 0.0

    @staticmethod
    def _place(location: dict, offset: float) -> PlaceRef:
        name = location.get("name", "Unknown")
        region = location.get("region", "") or ""
        country = location.get("country", "") or ""
        return PlaceRef(
            name=name,
            region=region,
            country=country,
            lat=location.get("lat", 0.0),
            lon=location.get("lon", 0.0),
            tz_id=location.get("tz_id", "") or "",
            utc_offset_hours=offset,
            localtime_epoch=location.get("localtime_epoch") or 0,
            localtime_iso=(location.get("localtime") or "").replace(" ", "T"),
            label=", ".join(p for p in (name, region, country) if p),
        )

    @staticmethod
    def _condition(block: dict, is_day: bool) -> Condition:
        described = conditions.describe(
            (block or {}).get("code"), (block or {}).get("text", ""), is_day
        )
        return Condition(**described)

    def _current(self, current: dict, offset: float) -> Observation:
        temp = current.get("temp_c", 0.0)
        humidity = current.get("humidity", 0)
        speed = current.get("wind_kph", 0.0)
        is_day = bool(current.get("is_day", 1))
        felt = thermal.feels_like(temp, humidity, speed)
        gust = current.get("gust_kph")
        force = wind.beaufort(speed)

        return Observation(
            observed_epoch=current.get("last_updated_epoch") or 0,
            is_day=is_day,
            condition=self._condition(current.get("condition"), is_day),
            temp_c=temp,
            # Prefer our own index: upstream feelslike_c does not say which one it used.
            feels_c=felt["value"],
            feels_basis=felt["basis"],
            humidity=humidity,
            dewpoint_c=current.get("dewpoint_c", round(thermal.dew_point_c(temp, humidity), 1)),
            pressure_mb=current.get("pressure_mb", 0.0),
            wind_kph=speed,
            wind_gust_kph=gust,
            wind_dir_deg=current.get("wind_degree", 0),
            wind_dir_16=current.get("wind_dir") or wind.cardinal(current.get("wind_degree")),
            beaufort_force=force["force"],
            beaufort_name=force["name"],
            cloud=current.get("cloud", 0),
            uv=current.get("uv", 0.0),
            precip_mm=current.get("precip_mm", 0.0),
            vis_km=current.get("vis_km"),
            snow_cm=0.0,
            heat_index_c=round(thermal.heat_index_c(temp, humidity), 1),
            wind_chill_c=round(thermal.wind_chill_c(temp, speed), 1),
            humidex_c=round(thermal.humidex(temp, humidity), 1),
        )

    def _hours(self, payload: dict, offset: float) -> list:
        out = []
        for day in (payload.get("forecast") or {}).get("forecastday") or []:
            for hour in day.get("hour") or []:
                temp = hour.get("temp_c", 0.0)
                humidity = hour.get("humidity", 0)
                speed = hour.get("wind_kph", 0.0)
                is_day = bool(hour.get("is_day", 1))
                out.append(HourPoint(
                    t=hour.get("time_epoch") or _epoch(hour.get("time"), offset) or 0,
                    temp_c=temp,
                    feels_c=thermal.feels_like(temp, humidity, speed)["value"],
                    dewpoint_c=hour.get("dewpoint_c", round(thermal.dew_point_c(temp, humidity), 1)),
                    humidity=humidity,
                    precip_mm=hour.get("precip_mm", 0.0),
                    chance_rain=hour.get("chance_of_rain", 0),
                    chance_snow=hour.get("chance_of_snow", 0),
                    wind_kph=speed,
                    gust_kph=hour.get("gust_kph"),
                    wind_dir_deg=hour.get("wind_degree", 0),
                    pressure_mb=hour.get("pressure_mb", 0.0),
                    cloud=hour.get("cloud", 0),
                    uv=hour.get("uv", 0.0),
                    vis_km=hour.get("vis_km"),
                    is_day=is_day,
                    condition=self._condition(hour.get("condition"), is_day),
                ))
        return out

    def _daily(self, payload: dict, offset: float) -> list:
        out = []
        for day in (payload.get("forecast") or {}).get("forecastday") or []:
            block = day.get("day") or {}
            astro = day.get("astro") or {}
            date_epoch = day.get("date_epoch") or _epoch(day.get("date"), offset) or 0
            sunrise = _clock_epoch(date_epoch, astro.get("sunrise", ""), offset)
            sunset = _clock_epoch(date_epoch, astro.get("sunset", ""), offset)
            daylight = round((sunset - sunrise) / 60) if sunrise and sunset else None
            illumination = astro.get("moon_illumination")
            out.append(DayPoint(
                date=day.get("date", ""),
                date_epoch=date_epoch,
                condition=self._condition(block.get("condition"), True),
                maxtemp_c=block.get("maxtemp_c", 0.0),
                mintemp_c=block.get("mintemp_c", 0.0),
                avgtemp_c=block.get("avgtemp_c", 0.0),
                maxwind_kph=block.get("maxwind_kph", 0.0),
                totalprecip_mm=block.get("totalprecip_mm", 0.0),
                totalsnow_cm=block.get("totalsnow_cm", 0.0),
                avghumidity=block.get("avghumidity", 0),
                chance_rain=block.get("daily_chance_of_rain", 0),
                chance_snow=block.get("daily_chance_of_snow", 0),
                uv=block.get("uv", 0.0),
                sunrise_epoch=sunrise,
                sunset_epoch=sunset,
                moonrise_epoch=_clock_epoch(date_epoch, astro.get("moonrise", ""), offset),
                moonset_epoch=_clock_epoch(date_epoch, astro.get("moonset", ""), offset),
                moon_phase=astro.get("moon_phase", "") or "",
                moon_illumination=float(illumination) if illumination not in (None, "") else None,
                daylight_minutes=daylight,
            ))
        return out

    @staticmethod
    def _air(raw: dict | None) -> AirQuality | None:
        if not raw:
            return None
        pollutants = {
            key: round(float(raw[key]), 2)
            for key in ("pm2_5", "pm10", "o3", "no2", "so2", "co")
            if raw.get(key) is not None
        }
        sub = {
            key: value for key, value in (
                (key, air.sub_index(key, pollutants.get(key))) for key in ("pm2_5", "pm10")
            ) if value is not None
        }
        aqi = max(sub.values()) if sub else None
        defra = raw.get("gb-defra-index")
        return AirQuality(
            pollutants=pollutants,
            sub_indices=sub,
            aqi_us=aqi,
            dominant=max(sub, key=sub.get) if sub else None,
            category=air.category(aqi),
            basis=air.BASIS,
            epa_index=raw.get("us-epa-index"),
            defra_index=defra,
            defra_label=air.defra_label(defra),
        )

    def _alerts(self, payload: dict, offset: float) -> list:
        rows = ((payload.get("alerts") or {}).get("alert")) or []
        out = []
        for index, row in enumerate(rows):
            severity = (row.get("severity") or "moderate").lower()
            out.append(Alert(
                id=f"{row.get('event', 'alert')}-{index}".lower().replace(" ", "-"),
                event=row.get("event", "") or "Weather alert",
                headline=row.get("headline") or row.get("event") or "Weather alert",
                severity=severity,
                tone=_ALERT_TONES.get(severity, "warn"),
                areas=row.get("areas", "") or "",
                effective_epoch=_epoch(row.get("effective"), offset),
                expires_epoch=_epoch(row.get("expires"), offset),
                description=row.get("desc", "") or "",
                instruction=row.get("instruction", "") or "",
            ))
        return out

    def _marine(self, query: str, offset: float) -> tuple[Marine | None, str | None]:
        """Marine is a separate product and 400s for inland places; that is normal."""
        target = query
        if parse_latlon(query) is None:
            target = query
        try:
            payload = self._http.get_json(
                self._base + "marine.json", {"key": self._key, "q": target, "days": 1}
            )
        except ProviderError:
            return None, None

        days = (payload.get("forecast") or {}).get("forecastday") or []
        if not days:
            return None, None
        hours = days[0].get("hour") or []
        if not hours:
            return None, None
        sample = hours[min(12, len(hours) - 1)]
        return Marine(
            wave_m=sample.get("sig_ht_mt"),
            wave_period_s=sample.get("swell_period_secs"),
            swell_dir_deg=sample.get("swell_dir"),
            water_temp_c=sample.get("water_temp_c"),
            hours=[
                {
                    "t": hour.get("time_epoch"),
                    "wave_m": hour.get("sig_ht_mt"),
                    "period_s": hour.get("swell_period_secs"),
                    "dir_deg": hour.get("swell_dir"),
                }
                for hour in hours
            ],
        ), None
