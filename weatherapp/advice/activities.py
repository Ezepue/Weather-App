"""Activity scorers. Weightings are editorial judgement, kept in one file."""

from __future__ import annotations

from .registry import scorer


@scorer("running", "Running", "run")
def running(s):
    """Runners generate their own heat, so the ideal is cooler than 'pleasant'."""
    score, reasons = 100.0, []
    feels = s.feels_c
    if feels > 14:
        score -= min(55, (feels - 14) ** 1.25 * 1.9)
        if feels > 22:
            reasons.append(f"Too warm at {round(feels)}C apparent")
    elif feels < -2:
        score -= min(35, (-2 - feels) * 3.2)
        reasons.append("Cold enough to need covered skin")
    if s.precip_mm > 0.4:
        score -= min(25, s.precip_mm * 10)
        reasons.append("Wet underfoot")
    if s.wind_kph > 30:
        score -= min(20, (s.wind_kph - 30) * 0.7)
        reasons.append("Headwind on the return leg")
    if s.humidity > 80 and s.temp_c > 18:
        score -= 12
        reasons.append("Muggy - sweat will not evaporate")
    if s.aqi_epa and s.aqi_epa >= 3:
        score -= (s.aqi_epa - 2) * 14
        reasons.append("Air quality poor for hard breathing")
    if s.uv >= 8:
        score -= 8
        reasons.append("Strong UV - go early or late")
    return score, reasons, {}


@scorer("cycling", "Cycling", "bike")
def cycling(s):
    """Wind matters roughly twice as much on a bike as on foot."""
    score, reasons = 100.0, []
    feels = s.feels_c
    if feels < 5:
        score -= min(30, (5 - feels) * 2.6)
        reasons.append("Cold hands weather")
    if feels > 28:
        score -= min(30, (feels - 28) * 2.4)
        reasons.append("Hot - carry more water")
    if s.wind_kph > 18:
        score -= min(38, (s.wind_kph - 18) * 1.3)
        reasons.append(f"{round(s.wind_kph)} km/h wind")
    if s.gust_kph and s.gust_kph - s.wind_kph > 25:
        score -= 14
        reasons.append("Gusty - unstable on exposed roads")
    if s.precip_mm > 0.2:
        score -= min(32, s.precip_mm * 13)
        reasons.append("Wet roads, longer braking")
    if s.vis_km is not None and s.vis_km < 4:
        score -= 22
        reasons.append("Poor visibility - be seen")
    return score, reasons, {}


@scorer("laundry", "Laundry", "laundry")
def laundry(s):
    """Drying is evaporation: warmth, dryness and air movement, in that order."""
    score, reasons = 20.0, []
    score += min(30, max(0.0, s.temp_c - 4) * 1.7)
    score += min(28, max(0.0, 85 - s.humidity) * 0.5)
    score += min(24, s.wind_kph * 1.1)
    score += min(10, max(0.0, 60 - s.cloud) * 0.16)
    if s.precip_mm > 0.05:
        score = min(score, 12)
        reasons.append("Rain - it comes in wetter than it went out")
    if s.humidity > 85:
        reasons.append("Air already saturated")
    if s.temp_c < 4:
        reasons.append("Too cold to evaporate much")
    if s.daylight_hours < 8:
        score -= 8
        reasons.append("Short drying day")
    if not reasons:
        reasons.append(f"Dry air and {round(s.wind_kph)} km/h of breeze")
    return score, reasons, {}


@scorer("stargazing", "Stargazing", "stars")
def stargazing(s):
    score, reasons = 100.0, []
    score -= s.cloud * 0.72
    if s.cloud > 40:
        reasons.append(f"{round(s.cloud)}% cloud cover")
    if s.moon_illumination is not None:
        score -= s.moon_illumination * 0.22
        if s.moon_illumination > 65:
            reasons.append(f"Moon {round(s.moon_illumination)}% lit - washes out faint objects")
    if s.precip_mm > 0:
        score -= 25
        reasons.append("Precipitation")
    if s.vis_km is not None and s.vis_km < 8:
        score -= 18
        reasons.append("Haze near the horizon")
    if s.humidity > 92:
        score -= 10
        reasons.append("Dew will settle on optics")
    return score, reasons, {}


@scorer("beach", "Beach", "beach")
def beach(s):
    score, reasons = 40.0, []
    score += min(40, max(0.0, s.temp_c - 16) * 3.4)
    if s.temp_c < 18:
        reasons.append("Too cool to sit still in swimwear")
    score += min(12, max(0.0, 70 - s.cloud) * 0.18)
    if s.wind_kph > 25:
        score -= min(28, (s.wind_kph - 25) * 1.1)
        reasons.append("Sand-blasting wind")
    if s.precip_mm > 0.1:
        score -= 40
        reasons.append("Rain")
    if s.uv >= 9:
        score -= 6
        reasons.append("Extreme UV - shade between swims")
    if s.water_temp_c is not None:
        if s.water_temp_c >= 20:
            score += 8
        elif s.water_temp_c < 14:
            score -= 10
            reasons.append(f"Water only {round(s.water_temp_c)}C")
    if not reasons:
        reasons.append("Warm, bright and calm")
    return score, reasons, {"water_temp_c": s.water_temp_c}


@scorer("gardening", "Gardening", "plant")
def gardening(s):
    score, reasons = 100.0, []
    if s.precip_mm > 0.3:
        score -= 35
        reasons.append("Raining now - soil compacts underfoot")
    if s.temp_c < 3:
        score -= 30
        reasons.append("Ground too cold to plant")
    if s.temp_c > 32:
        score -= 22
        reasons.append("Heat stress on transplants")
    if s.wind_kph > 35:
        score -= 18
        reasons.append("Too windy to spray or sow")
    if s.frost and s.frost.get("risk"):
        score -= 25
        reasons.append(s.frost.get("note") or "Frost risk")

    if s.next_24h_precip_mm >= 4:
        watering = "Skip watering - rain is coming"
    elif s.temp_c > 24 and s.next_24h_precip_mm < 1:
        watering = "Water deeply this evening"
    else:
        watering = "Normal watering"
    return score, reasons, {"watering": watering}


@scorer("photography", "Photography", "camera")
def photography(s):
    """Broken cloud is the sweet spot; clear and overcast are both flat light."""
    score, reasons = 60.0, []
    score += 35 - abs(s.cloud - 45) * 0.7
    if s.cloud < 10:
        reasons.append("Cloudless - hard light, empty sky")
    elif s.cloud > 85:
        reasons.append("Flat overcast - no direction to the light")
    else:
        reasons.append("Broken cloud - texture and shaped light")
    if s.vis_km is not None:
        if s.vis_km > 15:
            score += 8
        elif s.vis_km < 5:
            score -= 15
            reasons.insert(0, "Murky distance")
    if s.precip_mm > 0.5:
        score -= 18
        reasons.insert(0, "Keep the body dry")
    return score, reasons, {"golden_hour_epoch": s.golden_evening_epoch}


@scorer("kite", "Kite & sail", "kite")
def kite(s):
    """Wind sports invert the usual scoring: too little wind is the failure."""
    score, reasons = 100.0, []
    if s.wind_kph < 14:
        score -= (14 - s.wind_kph) * 5.5
        reasons.append(f"Only {round(s.wind_kph)} km/h - not enough to fly")
    elif s.wind_kph > 45:
        score -= (s.wind_kph - 45) * 2.4
        reasons.append("Overpowered - too strong for most kites")
    else:
        reasons.append(f"{round(s.wind_kph)} km/h in the usable band")
    if s.gust_kph and s.gust_kph - s.wind_kph > 20:
        score -= 18
        reasons.append("Gusty and unpredictable")
    if s.precip_mm > 0.5:
        score -= 20
        reasons.append("Wet lines")
    return score, reasons, {}
