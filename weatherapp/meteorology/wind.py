"""Wind description, including the data a synoptic wind barb needs."""

from __future__ import annotations

from .units import kph_to_knots

CARDINALS_16 = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)

_BEAUFORT = (
    (1, 0, "Calm", "Smoke rises vertically"),
    (6, 1, "Light air", "Smoke drifts"),
    (12, 2, "Light breeze", "Leaves rustle"),
    (20, 3, "Gentle breeze", "Flags extend"),
    (29, 4, "Moderate breeze", "Dust and loose paper lift"),
    (39, 5, "Fresh breeze", "Small trees sway"),
    (50, 6, "Strong breeze", "Umbrellas hard to use"),
    (62, 7, "Near gale", "Walking into wind is work"),
    (75, 8, "Gale", "Twigs break off trees"),
    (89, 9, "Strong gale", "Roof tiles lift"),
    (103, 10, "Storm", "Trees uprooted"),
    (118, 11, "Violent storm", "Widespread damage"),
)


def cardinal(deg: float | None) -> str:
    if deg is None:
        return "--"
    return CARDINALS_16[int((deg % 360) / 22.5 + 0.5) % 16]


def beaufort(kph: float | None) -> dict:
    if kph is None:
        return {"force": None, "name": "Unknown", "note": ""}
    for ceiling, force, name, note in _BEAUFORT:
        if kph < ceiling:
            return {"force": force, "name": name, "note": note}
    return {"force": 12, "name": "Hurricane force", "note": "Devastation"}


def barb(kph: float | None) -> dict:
    """Decompose speed into the pennants/barbs/half-barbs a chart barb draws.

    Station-model convention: pennant 50 kt, full barb 10 kt, half barb 5 kt.
    """
    if kph is None:
        return {"knots": 0, "pennants": 0, "full": 0, "half": 0, "calm": True}
    knots = kph_to_knots(kph)
    rounded = int(round(knots / 5.0) * 5)
    if rounded < 3:
        return {"knots": rounded, "pennants": 0, "full": 0, "half": 0, "calm": True}
    pennants, remainder = divmod(rounded, 50)
    full, remainder = divmod(remainder, 10)
    return {
        "knots": rounded,
        "pennants": pennants,
        "full": full,
        "half": 1 if remainder >= 5 else 0,
        "calm": False,
    }
