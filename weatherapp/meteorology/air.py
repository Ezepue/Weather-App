"""Air quality, converted to the US EPA AQI scale."""

from __future__ import annotations

# 2012 EPA breakpoints. Only PM2.5 and PM10 are here: the gas pollutants are
# reported by the provider in ug/m3, but their breakpoints are defined in
# ppm/ppb, and converting needs a temperature and pressure we do not have.
_BREAKPOINTS = {
    "pm2_5": (
        (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500),
    ),
    "pm10": (
        (0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150),
        (255, 354, 151, 200), (355, 424, 201, 300), (425, 604, 301, 500),
    ),
}

CATEGORIES = (
    (50, "Good", "Air quality is satisfactory.", "ok"),
    (100, "Moderate", "Unusually sensitive people should limit long exertion outdoors.", "warn"),
    (150, "Unhealthy for sensitive groups", "Children, older adults and people with heart or lung conditions should cut back.", "warn"),
    (200, "Unhealthy", "Everyone should reduce prolonged exertion outdoors.", "bad"),
    (300, "Very unhealthy", "Avoid outdoor exertion. Keep windows closed.", "bad"),
    (10_000, "Hazardous", "Health emergency. Stay indoors with filtered air.", "bad"),
)

_DEFRA_BANDS = ((3, "Low"), (6, "Moderate"), (9, "High"), (10, "Very high"))

POLLUTANT_LABELS = {
    "pm2_5": "PM2.5", "pm10": "PM10", "o3": "Ozone",
    "no2": "NO2", "so2": "SO2", "co": "CO",
}

BASIS = "US EPA AQI from PM2.5 / PM10; gas breakpoints require ppm, not reported"


def sub_index(pollutant: str, value: float | None) -> int | None:
    table = _BREAKPOINTS.get(pollutant)
    if table is None or value is None:
        return None
    for c_low, c_high, i_low, i_high in table:
        if value <= c_high:
            value = max(value, c_low)
            return round((i_high - i_low) / (c_high - c_low) * (value - c_low) + i_low)
    return 500


def category(aqi: float | None) -> dict:
    if aqi is None:
        return {"label": "Unknown", "advice": "", "tone": "neutral"}
    for ceiling, label, advice, tone in CATEGORIES:
        if aqi <= ceiling:
            return {"label": label, "advice": advice, "tone": tone}
    return {"label": "Hazardous", "advice": "Stay indoors.", "tone": "bad"}


def defra_label(index: int | None) -> str | None:
    if index is None:
        return None
    for ceiling, label in _DEFRA_BANDS:
        if index <= ceiling:
            return label
    return "Very high"
