"""A single 0-100 composite for how the outdoors will treat a person."""

from __future__ import annotations

_BANDS = (
    (88, "Sublime", "ok"),
    (74, "Pleasant", "ok"),
    (58, "Fair", "warn"),
    (40, "Taxing", "warn"),
    (22, "Punishing", "bad"),
    (-1, "Hostile", "bad"),
)

IDEAL_LOW, IDEAL_HIGH = 18.0, 24.0


def comfort(snapshot) -> dict:
    feels = snapshot.feels_c
    penalties: list[tuple[str, float]] = []

    # Cold and heat are deliberately asymmetric. Below the comfort band a
    # person can add layers, so the penalty grows almost linearly; above it
    # there is no equivalent remedy, so it accelerates. A single shared curve
    # either flat-lines in the cold (-25C scoring the same as 0C) or lets
    # dangerous heat off too lightly.
    if feels < IDEAL_LOW:
        penalties.append(("temperature", min(95.0, ((IDEAL_LOW - feels) ** 1.05) * 2.2)))
    elif feels > IDEAL_HIGH:
        penalties.append(("temperature", min(95.0, ((feels - IDEAL_HIGH) ** 1.30) * 2.6)))

    if snapshot.humidity > 62:
        penalties.append(("humidity", min(18.0, (snapshot.humidity - 62) * 0.42)))
    elif snapshot.humidity < 28:
        penalties.append(("dry air", min(12.0, (28 - snapshot.humidity) * 0.3)))

    if snapshot.wind_kph > 20:
        penalties.append(("wind", min(16.0, (snapshot.wind_kph - 20) * 0.45)))
    if snapshot.precip_mm:
        penalties.append(("rain", min(22.0, snapshot.precip_mm * 9.0)))
    if snapshot.uv > 5:
        penalties.append(("UV", min(10.0, (snapshot.uv - 5) * 2.4)))
    if snapshot.aqi_epa and snapshot.aqi_epa > 2:
        penalties.append(("air quality", min(24.0, (snapshot.aqi_epa - 2) * 7.0)))

    score = max(0.0, min(100.0, 100.0 - sum(cost for _, cost in penalties)))
    band, tone = next((b, t) for floor, b, t in _BANDS if score >= floor)
    penalties.sort(key=lambda item: -item[1])

    return {
        "score": round(score),
        "band": band,
        "tone": tone,
        "feels_c": feels,
        "detractors": [{"cause": c, "cost": round(v)} for c, v in penalties[:3] if v >= 1],
    }
