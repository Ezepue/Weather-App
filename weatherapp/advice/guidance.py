"""Direct answers: umbrella, sunscreen, what to wear, one-line summary."""

from __future__ import annotations

from ..meteorology import timeline, wind


def umbrella(snapshot) -> dict:
    windows = timeline.rain_windows(snapshot.hourly, snapshot.now_epoch)
    now = snapshot.now_epoch
    upcoming = [w for w in windows if w["end"] > now and w["start"] < now + 12 * 3600]
    if not upcoming:
        return {
            "needed": False,
            "verdict": "Leave it at home",
            "detail": "Nothing wet in the next 12 hours",
            "tone": "ok",
        }

    first = upcoming[0]
    total = round(sum(w["total_mm"] for w in upcoming), 1)
    minutes = max(0, int((first["start"] - now) / 60))
    if first["start"] <= now:
        easing = max(1, int((first["end"] - now) / 60))
        detail = f"Raining now, easing in about {easing} min"
    elif minutes < 90:
        detail = f"Rain starts in about {minutes} min"
    else:
        detail = f"Rain from about {minutes // 60}h from now"

    heavy = total >= 4 or first["peak_chance"] >= 80
    return {
        "needed": True,
        "verdict": "Take the umbrella" if heavy else "Worth a jacket",
        "detail": f"{detail} - {total} mm expected",
        "tone": "bad" if heavy else "warn",
        "starts": first["start"],
        "ends": first["end"],
    }


def sunscreen(snapshot) -> dict:
    """Burn time uses the common Fitzpatrick II approximation, 200 / (UV x 3).

    The peak looks 24 hours ahead, which at night is tomorrow lunchtime. Advice
    keyed off that peak alone told people to apply SPF 30 at midnight, so the
    current UV decides whether this is advice for now or a heads-up for later.
    """
    uv_max = snapshot.uv_max_today
    uv_now = snapshot.uv or 0
    _, peak_at = timeline.peak_uv(snapshot.hourly, snapshot.now_epoch)

    if uv_max < 3:
        return {"needed": False, "verdict": "Not needed today", "tone": "ok",
                "burn_minutes": None, "when": "none"}

    burn = int(200 / (uv_max * 3))
    if uv_now < 3:
        return {
            "needed": False,
            "verdict": "Not needed right now",
            "detail": f"UV is {round(uv_now, 1)}. It reaches {round(uv_max, 1)} later - "
                      f"about {burn} min to burn then.",
            "tone": "ok",
            "burn_minutes": burn,
            "peak_uv": round(uv_max, 1),
            "peak_at": peak_at,
            "when": "later",
        }
    return {
        "needed": True,
        "verdict": f"SPF 30+ - unprotected skin burns in about {burn} min",
        "tone": "warn" if uv_max < 8 else "bad",
        "burn_minutes": burn,
        "peak_uv": round(uv_max, 1),
        "peak_at": peak_at,
        "when": "now",
    }


_LAYERS = (
    (-8, "Serious cold - cover every exposed edge",
     ("Thermal base layer", "Insulated mid layer", "Windproof parka"),
     ("Hat that covers the ears", "Insulated gloves", "Scarf")),
    (0, "Freezing - full winter kit",
     ("Long-sleeve base", "Fleece or wool mid", "Winter coat"), ("Gloves", "Hat")),
    (8, "Cold - three thin layers beat one thick one",
     ("Long sleeves", "Warm jumper", "Coat"), ("Light gloves if out after dark",)),
    (14, "Cool - a jacket you can carry", ("Long sleeves", "Light jacket"), ()),
    (20, "Mild - one layer you can shed", ("Long or short sleeves", "Light overshirt"), ()),
    (26, "Warm - single light layer", ("Short sleeves", "Light trousers or shorts"), ()),
    (32, "Hot - loose and pale colours",
     ("Loose light cotton or linen", "Shorts"), ("Refill a water bottle",)),
    (999, "Dangerous heat - limit time outdoors",
     ("Lightest breathable fabric you own",), ("Water", "Plan shade for the middle of the day")),
)


def outfit(snapshot) -> dict:
    """Keyed off apparent temperature, because that is what skin responds to."""
    feels = snapshot.feels_c
    ceiling, headline, layers, base_extras = next(row for row in _LAYERS if feels <= row[0])
    extras = list(base_extras)

    if snapshot.precip_mm > 0.3 or snapshot.chance_rain >= 60:
        extras += ["Waterproof shell", "Shoes you do not mind soaking"]
    if snapshot.wind_kph > 35:
        extras.append("Windproof outer - an umbrella will invert")
    if snapshot.uv >= 6:
        extras.append("Sunglasses and a brim")
    if feels > 8 and 25 <= snapshot.chance_rain < 60 and snapshot.precip_mm <= 0.3:
        extras.append("Packable jacket just in case")

    return {
        "headline": headline,
        "feels_c": feels,
        "layers": list(layers),
        "extras": list(dict.fromkeys(extras)),
    }


def summary(place_name: str, current, first_day, umbrella_advice: dict) -> str:
    """One sentence for screen readers, the clipboard and the page title."""
    parts = [f"{place_name}: {current.condition.text.lower()}, {round(current.temp_c)} degrees"]
    if abs(current.feels_c - current.temp_c) >= 2:
        parts.append(f"feels like {round(current.feels_c)}")
    if first_day is not None:
        parts.append(f"high {round(first_day.maxtemp_c)}, low {round(first_day.mintemp_c)}")
    if current.wind_kph:
        parts.append(
            f"wind {round(current.wind_kph)} kilometres per hour from the "
            f"{wind.cardinal(current.wind_dir_deg)}"
        )
    parts.append(umbrella_advice["detail"].lower() if umbrella_advice["needed"] else "no rain expected")
    sentence = ". ".join(parts) + "."
    return sentence[0].upper() + sentence[1:]
