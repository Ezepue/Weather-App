"""Solar and lunar geometry.

Implements the NOAA General Solar Position Calculations so the UI can colour
itself from the real position of the sun rather than from the clock, and so we
can derive daylight length, golden/blue hour windows and a sun-path curve
without another API round trip.

All angles are degrees at the boundary, radians internally.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

# Reference new moon: 2000-01-06 18:14 UTC, mean synodic month in days.
_NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC_MONTH = 29.530588853

# Zenith angle of the geometric centre of the sun at apparent sunrise/sunset,
# including the standard 34' refraction plus the 16' solar semi-diameter.
_SUNRISE_ZENITH = 90.833

MOON_PHASE_NAMES = (
    "New Moon",
    "Waxing Crescent",
    "First Quarter",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
)


@dataclass
class SunPosition:
    elevation: float          # degrees above the horizon (negative = below)
    azimuth: float            # degrees clockwise from true north
    declination: float        # degrees
    equation_of_time: float   # minutes
    zenith: float             # degrees

    def as_dict(self) -> dict:
        return {k: round(v, 3) for k, v in asdict(self).items()}


def _fractional_year(when: datetime) -> float:
    when = when.astimezone(timezone.utc)
    day_of_year = int(when.strftime("%j"))
    hour = when.hour + when.minute / 60 + when.second / 3600
    return (2 * math.pi / 365.0) * (day_of_year - 1 + (hour - 12) / 24)


def _declination(gamma: float) -> float:
    """Solar declination in radians (NOAA truncated Fourier series)."""
    return (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.001480 * math.sin(3 * gamma)
    )


def _equation_of_time(gamma: float) -> float:
    """Equation of time in minutes."""
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def sun_position(when: datetime, lat: float, lon: float) -> SunPosition:
    """Position of the sun for an instant, seen from ``lat``/``lon``."""
    when = when.astimezone(timezone.utc)
    gamma = _fractional_year(when)
    decl = _declination(gamma)
    eqtime = _equation_of_time(gamma)

    minutes = when.hour * 60 + when.minute + when.second / 60
    true_solar_time = (minutes + eqtime + 4 * lon) % 1440
    hour_angle = math.radians(true_solar_time / 4 - 180)

    phi = math.radians(lat)
    cos_zenith = min(
        1.0,
        max(
            -1.0,
            math.sin(phi) * math.sin(decl)
            + math.cos(phi) * math.cos(decl) * math.cos(hour_angle),
        ),
    )
    zenith = math.acos(cos_zenith)

    azimuth = math.degrees(
        math.atan2(
            math.sin(hour_angle),
            math.cos(hour_angle) * math.sin(phi) - math.tan(decl) * math.cos(phi),
        )
    )
    azimuth = (azimuth + 180) % 360

    return SunPosition(
        elevation=90 - math.degrees(zenith),
        azimuth=azimuth,
        declination=math.degrees(decl),
        equation_of_time=eqtime,
        zenith=math.degrees(zenith),
    )


def _event_utc(day: datetime, lat: float, lon: float, zenith_deg: float, rising: bool):
    """UTC datetime at which the sun crosses ``zenith_deg``, or None."""
    day = day.astimezone(timezone.utc)
    noon_guess = day.replace(hour=12, minute=0, second=0, microsecond=0)
    gamma = _fractional_year(noon_guess)
    decl = _declination(gamma)
    eqtime = _equation_of_time(gamma)

    phi = math.radians(lat)
    zen = math.radians(zenith_deg)
    denominator = math.cos(phi) * math.cos(decl)
    if abs(denominator) < 1e-9:
        return None
    cos_ha = math.cos(zen) / denominator - math.tan(phi) * math.tan(decl)
    if cos_ha > 1 or cos_ha < -1:
        return None  # polar day or polar night
    ha = math.degrees(math.acos(cos_ha))
    if not rising:
        ha = -ha
    minutes = 720 - 4 * (lon + ha) - eqtime
    return noon_guess.replace(hour=0, minute=0) + timedelta(minutes=minutes)


def solar_events(day: datetime, lat: float, lon: float) -> dict:
    """Sunrise/sunset/solar-noon plus civil twilight, all in UTC."""
    sunrise = _event_utc(day, lat, lon, _SUNRISE_ZENITH, True)
    sunset = _event_utc(day, lat, lon, _SUNRISE_ZENITH, False)
    dawn = _event_utc(day, lat, lon, 96.0, True)      # civil twilight begins
    dusk = _event_utc(day, lat, lon, 96.0, False)     # civil twilight ends
    golden_start = _event_utc(day, lat, lon, 84.0, True)   # sun at +6 deg
    golden_end = _event_utc(day, lat, lon, 84.0, False)

    daylight = None
    if sunrise and sunset:
        daylight = round((sunset - sunrise).total_seconds() / 60)
    elif sunrise is None and sunset is None:
        # Polar case: sun either never sets or never rises.
        noon = sun_position(day.replace(hour=12), lat, lon)
        daylight = 1440 if noon.elevation > 0 else 0

    return {
        "dawn": dawn,
        "sunrise": sunrise,
        "solar_noon": _solar_noon(day, lon),
        "sunset": sunset,
        "dusk": dusk,
        "golden_morning_end": golden_start,
        "golden_evening_start": golden_end,
        "daylight_minutes": daylight,
    }


def _solar_noon(day: datetime, lon: float) -> datetime:
    day = day.astimezone(timezone.utc)
    gamma = _fractional_year(day.replace(hour=12))
    eqtime = _equation_of_time(gamma)
    minutes = 720 - 4 * lon - eqtime
    return day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)


def sun_path(day: datetime, lat: float, lon: float, samples: int = 49) -> list:
    """Sampled elevation curve for a day, for drawing the sun-path chart."""
    day = day.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    step = 1440 / (samples - 1)
    out = []
    for i in range(samples):
        moment = day + timedelta(minutes=i * step)
        pos = sun_position(moment, lat, lon)
        out.append(
            {
                "t": int(moment.timestamp()),
                "elevation": round(pos.elevation, 2),
                "azimuth": round(pos.azimuth, 2),
            }
        )
    return out


def moon_phase(when: datetime) -> dict:
    """Approximate lunar age, illuminated fraction and phase name."""
    when = when.astimezone(timezone.utc)
    days = (when - _NEW_MOON_EPOCH).total_seconds() / 86400.0
    age = days % _SYNODIC_MONTH
    fraction_of_cycle = age / _SYNODIC_MONTH
    # Illumination from the phase angle; exact enough for a phase disc.
    illumination = (1 - math.cos(2 * math.pi * fraction_of_cycle)) / 2
    index = int((fraction_of_cycle * 8 + 0.5)) % 8
    return {
        "age_days": round(age, 2),
        "fraction": round(fraction_of_cycle, 4),
        "illumination": round(illumination * 100, 1),
        "name": MOON_PHASE_NAMES[index],
        "waxing": fraction_of_cycle < 0.5,
    }


def daylight_delta(day: datetime, lat: float, lon: float) -> float | None:
    """Change in daylight length versus the previous day, in minutes."""
    today = solar_events(day, lat, lon)["daylight_minutes"]
    yesterday = solar_events(day - timedelta(days=1), lat, lon)["daylight_minutes"]
    if today is None or yesterday is None:
        return None
    return round(today - yesterday, 1)
