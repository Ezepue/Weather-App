"""Canonical condition vocabulary.

WeatherAPI reports 40-odd numeric condition codes; the demo provider invents
weather from a climate model.  Both are collapsed onto one small set of slugs
so the front end only has to know how to draw sixteen symbols, and so the
symbol set matches synoptic chart convention rather than cartoon icons.
"""

from __future__ import annotations

# slug -> (label, synoptic family, precipitation flag)
CONDITIONS = {
    "clear": ("Clear", "clear", False),
    "mostly-clear": ("Mostly clear", "clear", False),
    "partly-cloudy": ("Partly cloudy", "cloud", False),
    "cloudy": ("Cloudy", "cloud", False),
    "overcast": ("Overcast", "cloud", False),
    "mist": ("Mist", "obscuration", False),
    "fog": ("Fog", "obscuration", False),
    "drizzle": ("Drizzle", "rain", True),
    "rain-light": ("Light rain", "rain", True),
    "rain": ("Rain", "rain", True),
    "rain-heavy": ("Heavy rain", "rain", True),
    "sleet": ("Sleet", "mixed", True),
    "snow-light": ("Light snow", "snow", True),
    "snow": ("Snow", "snow", True),
    "snow-heavy": ("Heavy snow", "snow", True),
    "blizzard": ("Blizzard", "snow", True),
    "hail": ("Ice pellets", "mixed", True),
    "thunder": ("Thunder possible", "storm", False),
    "thunder-rain": ("Thunderstorm", "storm", True),
}

_CODE_MAP = {
    1000: "clear", 1003: "partly-cloudy", 1006: "cloudy", 1009: "overcast",
    1030: "mist", 1135: "fog", 1147: "fog",
    1063: "rain-light", 1150: "drizzle", 1153: "drizzle",
    1168: "drizzle", 1171: "drizzle", 1072: "drizzle",
    1180: "rain-light", 1183: "rain-light", 1186: "rain", 1189: "rain",
    1192: "rain-heavy", 1195: "rain-heavy", 1198: "sleet", 1201: "sleet",
    1240: "rain-light", 1243: "rain", 1246: "rain-heavy",
    1066: "snow-light", 1069: "sleet", 1204: "sleet", 1207: "sleet",
    1210: "snow-light", 1213: "snow-light", 1216: "snow", 1219: "snow",
    1222: "snow-heavy", 1225: "snow-heavy",
    1255: "snow-light", 1258: "snow",
    1114: "blizzard", 1117: "blizzard",
    1237: "hail", 1249: "sleet", 1252: "sleet", 1261: "hail", 1264: "hail",
    1087: "thunder", 1273: "thunder-rain", 1276: "thunder-rain",
    1279: "thunder-rain", 1282: "thunder-rain",
}


def slug_for_code(code: int | None, fallback_text: str = "") -> str:
    if code in _CODE_MAP:
        return _CODE_MAP[code]
    text = (fallback_text or "").lower()
    for needle, slug in (
        ("thunder", "thunder-rain"), ("blizzard", "blizzard"), ("snow", "snow"),
        ("sleet", "sleet"), ("hail", "hail"), ("ice", "hail"),
        ("drizzle", "drizzle"), ("downpour", "rain-heavy"), ("rain", "rain"), ("shower", "rain"),
        ("fog", "fog"), ("mist", "mist"), ("overcast", "overcast"),
        ("cloud", "partly-cloudy"), ("sun", "clear"), ("clear", "clear"),
    ):
        if needle in text:
            return slug
    return "partly-cloudy"


def label_for(slug: str) -> str:
    return CONDITIONS.get(slug, CONDITIONS["partly-cloudy"])[0]


def family_for(slug: str) -> str:
    return CONDITIONS.get(slug, CONDITIONS["partly-cloudy"])[1]


def is_wet(slug: str) -> bool:
    return CONDITIONS.get(slug, CONDITIONS["partly-cloudy"])[2]


def describe(code: int | None, text: str = "", is_day: bool = True) -> dict:
    slug = slug_for_code(code, text)
    return {
        "code": code,
        "slug": slug,
        "text": text or label_for(slug),
        "family": family_for(slug),
        "wet": is_wet(slug),
        "is_day": bool(is_day),
    }


def from_model(cloud: float, precip_mm: float, temp_c: float, thunder: bool = False) -> dict:
    """Pick a condition from modelled variables (used by the demo provider)."""
    if precip_mm >= 0.05:
        frozen = temp_c <= 0.5
        mixed = 0.5 < temp_c <= 2.5
        if thunder and not frozen:
            slug = "thunder-rain"
        elif frozen:
            slug = "blizzard" if precip_mm > 2.5 else ("snow-heavy" if precip_mm > 1.4 else ("snow" if precip_mm > 0.5 else "snow-light"))
        elif mixed:
            slug = "sleet"
        elif precip_mm > 4.0:
            slug = "rain-heavy"
        elif precip_mm > 1.2:
            slug = "rain"
        elif precip_mm > 0.35:
            slug = "rain-light"
        else:
            slug = "drizzle"
    elif thunder:
        slug = "thunder"
    elif cloud >= 92:
        slug = "overcast"
    elif cloud >= 68:
        slug = "cloudy"
    elif cloud >= 32:
        slug = "partly-cloudy"
    elif cloud >= 12:
        slug = "mostly-clear"
    else:
        slug = "clear"
    return {
        "code": None,
        "slug": slug,
        "text": label_for(slug),
        "family": family_for(slug),
        "wet": is_wet(slug),
        "is_day": True,
    }
