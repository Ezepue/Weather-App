"""Thermal comfort indices, as published by the issuing weather services."""

from __future__ import annotations

import math

from .units import c_to_f, f_to_c, kph_to_mph, kph_to_ms

UV_BANDS = (
    (2.5, "Low", "No protection needed"),
    (5.5, "Moderate", "Shade near midday"),
    (7.5, "High", "Sunscreen and a hat"),
    (10.5, "Very high", "Avoid midday sun"),
    (99.0, "Extreme", "Stay indoors 11:00-16:00"),
)


def dew_point_c(temp_c: float, humidity: float) -> float:
    """Magnus-Tetens."""
    rh = min(100.0, max(0.5, humidity))
    a, b = 17.625, 243.04
    alpha = math.log(rh / 100.0) + (a * temp_c) / (b + temp_c)
    return (b * alpha) / (a - alpha)


def relative_humidity(temp_c: float, dewpoint_c: float) -> float:
    """Inverse of dew_point_c, used to keep synthetic data self-consistent."""
    a, b = 17.625, 243.04
    numerator = math.exp((a * dewpoint_c) / (b + dewpoint_c))
    denominator = math.exp((a * temp_c) / (b + temp_c))
    return max(1.0, min(100.0, 100.0 * numerator / denominator))


def heat_index_c(temp_c: float, humidity: float) -> float:
    """NWS Rothfusz regression with both RH adjustments."""
    t = c_to_f(temp_c)
    r = min(100.0, max(0.0, humidity))

    simple = 0.5 * (t + 61.0 + ((t - 68.0) * 1.2) + (r * 0.094))
    if (simple + t) / 2 < 80.0:
        return f_to_c(simple)

    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * r
        - 0.22475541 * t * r
        - 0.00683783 * t * t
        - 0.05481717 * r * r
        + 0.00122874 * t * t * r
        + 0.00085282 * t * r * r
        - 0.00000199 * t * t * r * r
    )
    if r < 13 and 80 <= t <= 112:
        hi -= ((13 - r) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
    elif r > 85 and 80 <= t <= 87:
        hi += ((r - 85) / 10) * ((87 - t) / 5)
    return f_to_c(hi)


def wind_chill_c(temp_c: float, wind_kph: float) -> float:
    """NWS wind chill, which is only defined at or below 10C above 4.8 km/h."""
    if temp_c > 10 or wind_kph <= 4.8:
        return temp_c
    t = c_to_f(temp_c)
    v = kph_to_mph(wind_kph)
    return f_to_c(35.74 + 0.6215 * t - 35.75 * (v ** 0.16) + 0.4275 * t * (v ** 0.16))


def apparent_temp_c(temp_c: float, humidity: float, wind_kph: float) -> float:
    """Australian BOM apparent temperature - the only index valid at all temps."""
    vapour = (humidity / 100.0) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    return temp_c + 0.33 * vapour - 0.70 * kph_to_ms(wind_kph) - 4.00


def humidex(temp_c: float, humidity: float) -> float:
    dew = dew_point_c(temp_c, humidity)
    e = 6.11 * math.exp(5417.7530 * ((1 / 273.16) - (1 / (273.15 + dew))))
    return temp_c + 0.5555 * (e - 10.0)


def feels_like(temp_c: float, humidity: float, wind_kph: float) -> dict:
    """Pick the index a forecaster would actually quote at this temperature."""
    if temp_c <= 10 and wind_kph > 4.8:
        value, basis = wind_chill_c(temp_c, wind_kph), "wind chill"
    elif temp_c >= 27:
        value, basis = heat_index_c(temp_c, humidity), "heat index"
    else:
        value, basis = apparent_temp_c(temp_c, humidity, wind_kph), "apparent temperature"
    return {"value": round(value, 1), "basis": basis, "delta": round(value - temp_c, 1)}


def uv_band(uv: float | None) -> dict:
    if uv is None:
        return {"label": "Unknown", "advice": "", "tone": "neutral"}
    for ceiling, label, advice in UV_BANDS:
        if uv < ceiling:
            tone = "ok" if ceiling <= 5.5 else ("warn" if ceiling <= 7.5 else "bad")
            return {"label": label, "advice": advice, "tone": tone}
    return {"label": "Extreme", "advice": "Stay indoors 11:00-16:00", "tone": "bad"}
