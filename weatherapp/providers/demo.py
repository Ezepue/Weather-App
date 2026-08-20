"""Synthetic but physically coupled weather, for running without an API key.

The variables are not independent noise. A pressure wave drives cloud cover;
cloud attenuates UV and damps the diurnal temperature range; dew point is held
quasi-constant within an air mass so humidity peaks overnight on its own; rain
washes out particulates. That coupling is what makes the output read as weather
rather than as random numbers, and it keeps every panel in the UI consistent
with every other one.

Output is a pure function of (place, date), so tests and screenshots are stable.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import places
from ..domain.models import (
    AirQuality, Alert, Condition, DayPoint, HourPoint, Marine, Observation,
    PlaceRef, ProviderBundle,
)
from ..meteorology import air, conditions, solar, thermal, wind
from .base import parse_latlon, stable_seed

_HOUR = 3600
_SEA_LEVEL_MB = 1013.5

# DEFRA PM2.5 band upper bounds, index 1-10.
_DEFRA_PM25_BOUNDS = (11, 23, 35, 41, 47, 53, 58, 64, 70)

_SEVERITY = {
    "clear": 0, "mostly-clear": 1, "partly-cloudy": 2, "cloudy": 3, "overcast": 4,
    "mist": 5, "fog": 6, "drizzle": 7, "rain-light": 8, "rain": 9, "sleet": 10,
    "snow-light": 11, "rain-heavy": 12, "snow": 13, "hail": 14, "snow-heavy": 15,
    "thunder": 16, "blizzard": 17, "thunder-rain": 18,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class _Field:
    """A deterministic sum-of-sines field, seeded per place."""

    def __init__(self, seed: int):
        self._phases = [
            ((seed >> (i * 7)) & 0xFFFF) / 0xFFFF * 2 * math.pi for i in range(9)
        ]

    def wave(self, index: int, period_hours: float, epoch: int) -> float:
        phase = self._phases[index % len(self._phases)]
        return math.sin(2 * math.pi * epoch / (period_hours * _HOUR) + phase)


def _zone(tz_id: str, fallback_hours: float):
    try:
        return ZoneInfo(tz_id)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return timezone(timedelta(hours=fallback_hours))


def _synthetic_place(lat: float, lon: float) -> places.Place:
    """Climate normals estimated from latitude, for coordinates off the gazetteer."""
    abs_lat = abs(lat)
    offset = round(lon / 15)
    return places.Place(
        name=f"{lat:.2f}, {lon:.2f}",
        region="",
        country="Coordinates",
        lat=lat,
        lon=lon,
        tz_id=f"Etc/GMT{-offset:+d}" if offset else "UTC",
        utc_offset_fallback=offset,
        mean_c=28.0 - 0.42 * abs_lat,
        season_amp_c=1.2 + abs_lat * 0.20,
        diurnal_c=8.0 + 4.0 * (1 - min(1.0, abs_lat / 55)),
        base_rh=72.0,
        wetness=0.35,
        wind_kph=15.0,
        pm25_base=18.0,
        coastal=False,
    )


class DemoProvider:
    name = "demo"

    def __init__(self, clock, default_place: str = "London"):
        self._clock = clock
        self._default_place = default_place

    # ---- WeatherProvider ------------------------------------------------

    def search(self, query: str, limit: int = 8) -> list[dict]:
        coords = parse_latlon(query)
        if coords:
            lat, lon = coords
            return [{
                "name": f"{lat:.4f}, {lon:.4f}", "region": "", "country": "Coordinates",
                "lat": lat, "lon": lon, "tz_id": "UTC",
                "label": f"{lat:.4f}, {lon:.4f}",
            }]
        return places.search(query, limit)

    def fetch(self, query: str, days: int = 3) -> ProviderBundle:
        place = self._resolve(query or self._default_place)
        zone = _zone(place.tz_id, place.utc_offset_fallback)
        now = self._clock.now().astimezone(zone)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        field = _Field(stable_seed(place.name, place.lat, place.lon))

        hours = [
            self._hour(place, field, start + timedelta(hours=i), zone)
            for i in range(24 * max(1, days))
        ]
        daily = [
            self._day(place, hours[i * 24:(i + 1) * 24], start + timedelta(days=i), zone)
            for i in range(max(1, days))
        ]
        current = self._current(place, field, now, hours)

        return ProviderBundle(
            place=self._place_ref(place, now, zone),
            current=current,
            hourly=hours,
            daily=daily,
            air=self._air(place, field, current, int(now.timestamp())),
            marine=self._marine(place, current, now) if place.coastal else None,
            alerts=self._alerts(place, daily),
            notices=["Demo data: physically modelled, not observed. Set API_KEY for live weather."],
        )

    # ---- resolution -----------------------------------------------------

    def _resolve(self, query: str) -> places.Place:
        coords = parse_latlon(query)
        if coords:
            return _synthetic_place(*coords)
        found = places.lookup(query)
        if found:
            return found
        # Unknown name: invent a stable location rather than failing, so the
        # demo never dead-ends on a place the gazetteer has not heard of.
        seed = stable_seed("place", query.strip().lower())
        lat = ((seed % 12_000) / 100.0) - 60.0
        lon = (((seed >> 20) % 36_000) / 100.0) - 180.0
        invented = _synthetic_place(lat, lon)
        return places.Place(**{**invented.__dict__, "name": query.strip().title(), "country": "Demo"})

    def _place_ref(self, place: places.Place, now_local: datetime, zone) -> PlaceRef:
        offset = now_local.utcoffset() or timedelta(0)
        return PlaceRef(
            name=place.name,
            region=place.region,
            country=place.country,
            lat=place.lat,
            lon=place.lon,
            tz_id=place.tz_id,
            utc_offset_hours=offset.total_seconds() / 3600,
            localtime_epoch=int(now_local.timestamp()),
            localtime_iso=now_local.strftime("%Y-%m-%dT%H:%M"),
            label=place.label,
        )

    # ---- the model ------------------------------------------------------

    def _state(self, place: places.Place, field: _Field, moment: datetime) -> dict:
        epoch = int(moment.timestamp())
        local = moment
        day_of_year = int(local.strftime("%j"))
        peak_doy = 205 if place.lat >= 0 else 22

        seasonal = place.mean_c + place.season_amp_c * math.cos(
            2 * math.pi * (day_of_year - peak_doy) / 365.25
        )

        pressure = _SEA_LEVEL_MB + 15 * field.wave(0, 127, epoch) + 5 * field.wave(1, 29, epoch)
        pressure_anomaly = (pressure - _SEA_LEVEL_MB) / 20.0

        cloud = _clamp(
            100 * (
                0.52
                - 0.42 * pressure_anomaly
                + 0.18 * field.wave(2, 13, epoch)
                + (place.wetness - 0.35) * 0.55
            ),
            0, 100,
        )

        sun = solar.sun_position(moment, place.lat, place.lon)
        hour_local = local.hour + local.minute / 60
        diurnal_range = place.diurnal_c * (1 - 0.45 * cloud / 100)
        synoptic = 3.4 * field.wave(3, 113, epoch) + 1.9 * field.wave(4, 53, epoch)
        temp = seasonal + synoptic + (diurnal_range / 2) * math.cos(
            2 * math.pi * (hour_local - 15) / 24
        )

        # One dew point per air mass; humidity then follows temperature.
        dew_target = seasonal - (100 - place.base_rh) * 0.28 + synoptic * 0.4
        dewpoint = min(dew_target + 1.2 * field.wave(5, 71, epoch), temp - 0.3)
        humidity = _clamp(thermal.relative_humidity(temp, dewpoint), 18, 100)

        rain_drive = max(0.0, (cloud - 70) / 30.0) * (0.35 + 1.3 * place.wetness)
        burst = field.wave(6, 37, epoch)
        precip = round(rain_drive * (0.3 + 2.2 * max(0.0, burst)), 2) if burst > 0.15 else 0.0

        gradient = abs(field.wave(0, 127, epoch + 3 * _HOUR) - field.wave(0, 127, epoch)) * 40
        speed = place.wind_kph * (0.5 + 0.9 * abs(field.wave(7, 43, epoch))) + gradient + cloud * 0.04
        gust = speed * (1.35 + 0.3 * abs(field.wave(2, 11, epoch)))
        direction = (place.lon * 3 + 140 * field.wave(8, 97, epoch)) % 360

        # Clear-sky UVI as a power of solar elevation. The exponent is fitted to
        # two anchors (tropical noon = 12, London midsummer = 7) and then lands
        # within 0.6 of published maxima from Phoenix to Tromso, so no latitude
        # fudge is needed - path length through the atmosphere does the work.
        # Thin cloud barely attenuates UV, hence the non-linear cloud term.
        sun_factor = max(0.0, math.sin(math.radians(sun.elevation))) ** 4.30
        uv = _clamp(12.0 * sun_factor * (1 - 0.70 * (cloud / 100) ** 1.8), 0, 13)

        foggy = humidity > 96 and speed < 9
        visibility = 0.6 if foggy else _clamp(32 - max(0.0, humidity - 60) * 0.28 - precip * 3.5, 0.4, 40)

        thunder = precip > 1.5 and temp > 18 and field.wave(6, 37, epoch) > 0.82
        condition = conditions.from_model(cloud, precip, temp, thunder)
        if foggy and precip < 0.05:
            condition = conditions.from_model(100, 0, temp)
            condition = {**condition, "slug": "fog", "text": "Fog", "family": "obscuration"}

        return {
            "epoch": epoch,
            "temp": temp,
            "dewpoint": dewpoint,
            "humidity": humidity,
            "pressure": pressure,
            "cloud": cloud,
            "precip": precip,
            "wind": speed,
            "gust": gust,
            "direction": direction,
            "uv": uv,
            "visibility": visibility,
            "elevation": sun.elevation,
            "condition": condition,
        }

    def _hour(self, place, field, moment: datetime, zone) -> HourPoint:
        state = self._state(place, field, moment)
        is_day = state["elevation"] > -0.833
        precip = state["precip"]
        snowing = state["temp"] <= 0.5
        return HourPoint(
            t=state["epoch"],
            temp_c=round(state["temp"], 1),
            feels_c=thermal.feels_like(state["temp"], state["humidity"], state["wind"])["value"],
            dewpoint_c=round(state["dewpoint"], 1),
            humidity=round(state["humidity"]),
            precip_mm=precip,
            chance_rain=0 if snowing else self._chance(state, place),
            chance_snow=self._chance(state, place) if snowing else 0,
            wind_kph=round(state["wind"], 1),
            gust_kph=round(state["gust"], 1),
            wind_dir_deg=round(state["direction"]) % 360,
            pressure_mb=round(state["pressure"], 1),
            cloud=round(state["cloud"]),
            uv=round(state["uv"], 1),
            vis_km=round(state["visibility"], 1),
            is_day=is_day,
            condition=Condition(**{**state["condition"], "is_day": is_day}),
        )

    @staticmethod
    def _chance(state: dict, place: places.Place) -> int:
        if state["precip"] > 0.2:
            return int(_clamp(70 + state["precip"] * 8, 70, 100))
        # Without modelled precipitation the chance must stay short of a promise.
        return int(_clamp((state["cloud"] - 55) * 1.6 * (0.5 + place.wetness), 0, 55))

    def _current(self, place, field, now: datetime, hours: list) -> Observation:
        state = self._state(place, field, now)
        is_day = state["elevation"] > -0.833
        felt = thermal.feels_like(state["temp"], state["humidity"], state["wind"])
        gust = state["gust"]
        return Observation(
            observed_epoch=state["epoch"],
            is_day=is_day,
            condition=Condition(**{**state["condition"], "is_day": is_day}),
            temp_c=round(state["temp"], 1),
            feels_c=felt["value"],
            feels_basis=felt["basis"],
            humidity=round(state["humidity"]),
            dewpoint_c=round(state["dewpoint"], 1),
            pressure_mb=round(state["pressure"], 1),
            wind_kph=round(state["wind"], 1),
            wind_gust_kph=round(gust, 1),
            wind_dir_deg=round(state["direction"]) % 360,
            wind_dir_16=wind.cardinal(state["direction"]),
            beaufort_force=wind.beaufort(state["wind"])["force"],
            beaufort_name=wind.beaufort(state["wind"])["name"],
            cloud=round(state["cloud"]),
            uv=round(state["uv"], 1),
            precip_mm=state["precip"],
            vis_km=round(state["visibility"], 1),
            snow_cm=round(state["precip"], 2) if state["temp"] <= 0.5 else 0.0,
            heat_index_c=round(thermal.heat_index_c(state["temp"], state["humidity"]), 1),
            wind_chill_c=round(thermal.wind_chill_c(state["temp"], state["wind"]), 1),
            humidex_c=round(thermal.humidex(state["temp"], state["humidity"]), 1),
        )

    def _day(self, place, hours: list, midnight: datetime, zone) -> DayPoint:
        events = solar.solar_events(midnight.astimezone(timezone.utc) + timedelta(hours=12), place.lat, place.lon)
        moon = solar.moon_phase(midnight.astimezone(timezone.utc) + timedelta(hours=12))
        daytime = [h for h in hours if h.is_day] or hours
        dominant = max(daytime, key=lambda h: _SEVERITY.get(h.condition.slug, 0))

        return DayPoint(
            date=midnight.strftime("%Y-%m-%d"),
            date_epoch=int(midnight.timestamp()),
            condition=dominant.condition,
            maxtemp_c=round(max(h.temp_c for h in hours), 1),
            mintemp_c=round(min(h.temp_c for h in hours), 1),
            avgtemp_c=round(sum(h.temp_c for h in hours) / len(hours), 1),
            maxwind_kph=round(max(h.wind_kph for h in hours), 1),
            totalprecip_mm=round(sum(h.precip_mm for h in hours), 2),
            totalsnow_cm=round(sum(h.precip_mm for h in hours if h.temp_c <= 0.5), 2),
            avghumidity=round(sum(h.humidity for h in hours) / len(hours)),
            chance_rain=max(h.chance_rain for h in hours),
            chance_snow=max(h.chance_snow for h in hours),
            uv=round(max(h.uv for h in hours), 1),
            sunrise_epoch=int(events["sunrise"].timestamp()) if events["sunrise"] else None,
            sunset_epoch=int(events["sunset"].timestamp()) if events["sunset"] else None,
            moon_phase=moon["name"],
            moon_illumination=moon["illumination"],
            daylight_minutes=events["daylight_minutes"],
        )

    def _air(self, place, field, current: Observation, epoch: int) -> AirQuality:
        stagnation = 1 + 0.6 * max(0.0, 1 - current.wind_kph / 18)
        washout = 1 - 0.35 * min(1.0, current.precip_mm)
        pm25 = _clamp(place.pm25_base * (0.55 + 0.9 * abs(field.wave(5, 67, epoch))) * stagnation * washout, 1, 400)
        pm10 = pm25 * 1.7
        pollutants = {
            "pm2_5": round(pm25, 2),
            "pm10": round(pm10, 2),
            "o3": round(_clamp(34 + current.uv * 6.2 + current.temp_c * 0.8, 5, 260), 2),
            "no2": round(_clamp(place.pm25_base * 0.42 * stagnation, 1, 200), 2),
            "so2": round(_clamp(place.pm25_base * 0.16, 0.5, 120), 2),
            "co": round(_clamp(190 + place.pm25_base * 4.1 * stagnation, 100, 4000), 2),
        }
        sub = {key: air.sub_index(key, pollutants[key]) for key in ("pm2_5", "pm10")}
        aqi = max(sub.values())
        dominant = max(sub, key=sub.get)
        defra = next((i + 1 for i, bound in enumerate(_DEFRA_PM25_BOUNDS) if pm25 <= bound), 10)
        epa = next((i for i, ceiling in enumerate((50, 100, 150, 200, 300), start=1) if aqi <= ceiling), 6)

        return AirQuality(
            pollutants=pollutants,
            sub_indices=sub,
            aqi_us=aqi,
            dominant=dominant,
            category=air.category(aqi),
            basis=air.BASIS,
            epa_index=epa,
            defra_index=defra,
            defra_label=air.defra_label(defra),
        )

    def _marine(self, place, current: Observation, now: datetime) -> Marine:
        # Fetch-limited wave growth: height rises roughly with wind to the 1.35.
        wave_m = _clamp(0.02 * current.wind_kph ** 1.35, 0.05, 12)
        day_of_year = int(now.strftime("%j"))
        peak_doy = 205 if place.lat >= 0 else 22
        # Sea surface lags air temperature by about a month and damps its swing.
        water = place.mean_c + 1.5 + 0.55 * place.season_amp_c * math.cos(
            2 * math.pi * (day_of_year - peak_doy - 30) / 365.25
        )
        return Marine(
            wave_m=round(wave_m, 2),
            wave_period_s=round(3.2 + wave_m * 1.7, 1),
            swell_dir_deg=round((current.wind_dir_deg + 18) % 360),
            water_temp_c=round(water, 1),
            hours=[],
        )

    def _alerts(self, place, daily: list) -> list:
        """Derived from the modelled data, so warnings never contradict the panels."""
        out: list[Alert] = []
        first = daily[0]
        rules = (
            (first.maxwind_kph > 75, "Wind", "Damaging wind warning",
             f"Gusts to {round(first.maxwind_kph)} km/h. Secure loose objects outdoors.", "severe"),
            (first.totalprecip_mm > 25, "Rain", "Heavy rainfall warning",
             f"{first.totalprecip_mm} mm expected in 24 hours. Surface flooding possible.", "moderate"),
            (first.maxtemp_c > 38, "Heat", "Extreme heat warning",
             f"Peak {round(first.maxtemp_c)}C. Avoid exertion between 11:00 and 16:00.", "severe"),
            (first.mintemp_c < -12, "Cold", "Extreme cold warning",
             f"Low of {round(first.mintemp_c)}C. Frostbite risk on exposed skin.", "severe"),
            (first.totalsnow_cm > 5, "Snow", "Snowfall warning",
             f"Around {first.totalsnow_cm} cm accumulation. Travel disruption likely.", "moderate"),
        )
        for index, (triggered, event, headline, description, severity) in enumerate(rules):
            if not triggered:
                continue
            out.append(Alert(
                id=f"demo-{place.name.lower().replace(' ', '-')}-{index}",
                event=event,
                headline=headline,
                severity=severity,
                tone="bad" if severity == "severe" else "warn",
                areas=place.label,
                effective_epoch=first.date_epoch,
                expires_epoch=first.date_epoch + 86_400,
                description=description,
                instruction="Modelled demo alert derived from the forecast values.",
            ))
        return out
