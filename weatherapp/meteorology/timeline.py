"""Reading a sequence of hours: pressure tendency, rain windows, extremes."""

from __future__ import annotations


def _as_dict(hour) -> dict:
    return hour if isinstance(hour, dict) else hour.__dict__ if hasattr(hour, "__dict__") else {
        f: getattr(hour, f) for f in hour.__slots__
    }


def _hours(hourly: list) -> list:
    return [_as_dict(h) for h in hourly]


def pressure_trend(hourly: list, now_epoch: int, current_mb: float | None) -> dict:
    """Three-hour barometric tendency, as a ship's log would record it."""
    unknown = {"delta_3h": None, "direction": "unknown", "label": "Unknown", "note": ""}
    if current_mb is None:
        return unknown
    past = [h for h in _hours(hourly) if h.get("t") is not None and h["t"] <= now_epoch and h.get("pressure_mb")]
    reference = next((h for h in reversed(past) if now_epoch - h["t"] >= 2.5 * 3600), None)
    reference = reference or (past[0] if past else None)
    if reference is None:
        return unknown

    hours = max(1.0, (now_epoch - reference["t"]) / 3600)
    rate = (current_mb - reference["pressure_mb"]) / hours * 3
    if rate <= -3:
        direction, label, note = "falling", "Falling fast", "Unsettled weather moving in"
    elif rate <= -1:
        direction, label, note = "falling", "Falling", "Cloud and rain more likely"
    elif rate < 1:
        direction, label, note = "steady", "Steady", "No big change expected"
    elif rate < 3:
        direction, label, note = "rising", "Rising", "Clearing and drying"
    else:
        direction, label, note = "rising", "Rising fast", "Brighter, breezier air arriving"
    return {
        "delta_3h": round(rate, 1),
        "direction": direction,
        "label": label,
        "note": note,
        "reference_mb": round(reference["pressure_mb"], 1),
    }


def rain_windows(hourly: list, now_epoch: int, threshold: float = 0.15) -> list:
    """Contiguous wet blocks in the next 30 hours."""
    windows: list = []
    current = None
    for hour in _hours(hourly):
        t = hour.get("t")
        if t is None or t < now_epoch - 3600:
            continue
        if t > now_epoch + 30 * 3600:
            break
        wet = (hour.get("precip_mm") or 0) >= threshold or (hour.get("chance_rain") or 0) >= 55
        if wet:
            current = current or {"start": t, "end": t, "total_mm": 0.0, "peak_chance": 0, "hours": 0}
            current["end"] = t + 3600
            current["total_mm"] += hour.get("precip_mm") or 0
            current["peak_chance"] = max(current["peak_chance"], hour.get("chance_rain") or 0)
            current["hours"] += 1
        elif current:
            windows.append(current)
            current = None
    if current:
        windows.append(current)
    for window in windows:
        window["total_mm"] = round(window["total_mm"], 2)
    return windows


def dry_windows(hourly: list, now_epoch: int, min_hours: int = 2) -> list:
    out: list = []
    run = None
    for hour in _hours(hourly):
        t = hour.get("t")
        if t is None or t < now_epoch - 3600:
            continue
        if t > now_epoch + 30 * 3600:
            break
        dry = (hour.get("precip_mm") or 0) < 0.1 and (hour.get("chance_rain") or 0) < 40
        if dry:
            run = run or {"start": t, "end": t, "hours": 0}
            run["end"] = t + 3600
            run["hours"] += 1
        elif run:
            if run["hours"] >= min_hours:
                out.append(run)
            run = None
    if run and run["hours"] >= min_hours:
        out.append(run)
    return out


def frost_risk(hourly: list, horizon_h: int = 18) -> dict:
    """Ground frost can form above zero air temperature when the air is dry."""
    window = [h for h in _hours(hourly)[:horizon_h] if h.get("temp_c") is not None]
    if not window:
        return {"risk": False, "level": "none", "note": ""}
    coldest = min(window, key=lambda h: h["temp_c"])
    temp, dew = coldest["temp_c"], coldest.get("dewpoint_c")
    if temp <= -2:
        level, note = "hard", "Hard frost - protect pipes and tender plants"
    elif temp <= 0:
        level, note = "frost", "Air frost expected"
    elif temp <= 3 and (dew is None or dew <= 1):
        level, note = "ground", "Ground frost possible on clear surfaces"
    else:
        return {"risk": False, "level": "none", "note": "", "min_c": round(temp, 1)}
    return {"risk": True, "level": level, "note": note, "min_c": round(temp, 1), "at": coldest.get("t")}


def air_out_window(hourly: list, now_epoch: int, indoor_c: float = 21.0) -> dict | None:
    """When to open the windows: dry, closest to indoor temperature, not gusty."""
    best = None
    for hour in _hours(hourly):
        t = hour.get("t")
        if t is None or t < now_epoch or t > now_epoch + 26 * 3600:
            continue
        if (hour.get("precip_mm") or 0) > 0.05 or hour.get("temp_c") is None:
            continue
        cost = abs(hour["temp_c"] - indoor_c) + max(0.0, (hour.get("wind_kph") or 0) - 25) * 0.2
        if best is None or cost < best[0]:
            best = (cost, hour)
    if best is None:
        return None
    _, hour = best
    return {
        "t": hour["t"],
        "temp_c": round(hour["temp_c"], 1),
        "wind_kph": hour.get("wind_kph"),
        "note": "Closest to indoor temperature and dry",
    }


def extremes(hourly: list, now_epoch: int, horizon_h: int = 24) -> dict:
    window = [
        h for h in _hours(hourly)
        if h.get("t") is not None and now_epoch <= h["t"] <= now_epoch + horizon_h * 3600
        and h.get("temp_c") is not None
    ]
    if not window:
        return {}
    warmest = max(window, key=lambda h: h["temp_c"])
    coldest = min(window, key=lambda h: h["temp_c"])
    return {
        "warmest": {"t": warmest["t"], "temp_c": round(warmest["temp_c"], 1)},
        "coldest": {"t": coldest["t"], "temp_c": round(coldest["temp_c"], 1)},
        "swing_c": round(warmest["temp_c"] - coldest["temp_c"], 1),
    }


def total_precip(hourly: list, now_epoch: int, horizon_h: int = 24) -> float:
    return round(sum(
        (h.get("precip_mm") or 0) for h in _hours(hourly)
        if h.get("t") is not None and now_epoch <= h["t"] <= now_epoch + horizon_h * 3600
    ), 2)


def peak_uv(hourly: list, now_epoch: int, horizon_h: int = 24) -> tuple[float, int | None]:
    best = (0.0, None)
    for hour in _hours(hourly):
        t = hour.get("t")
        if t is not None and now_epoch <= t <= now_epoch + horizon_h * 3600 and (hour.get("uv") or 0) > best[0]:
            best = (hour["uv"], t)
    return best
