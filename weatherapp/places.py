"""A small offline gazetteer.

Two jobs: it is the corpus the demo provider invents weather for, and it backs
type-ahead search when there is no upstream API key.  Climate columns are
coarse 30-year normals, enough to make demo data plausible for a place rather
than generically temperate.

Columns: name, region, country, lat, lon, tz_id, utc_offset_fallback,
mean_c (annual mean), season_amp_c, diurnal_c, base_rh, wetness (0-1),
wind_kph, pm25_base, coastal
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    name: str
    region: str
    country: str
    lat: float
    lon: float
    tz_id: str
    utc_offset_fallback: float
    mean_c: float
    season_amp_c: float
    diurnal_c: float
    base_rh: float
    wetness: float
    wind_kph: float
    pm25_base: float
    coastal: bool = False

    @property
    def key(self) -> str:
        return self.name.lower()

    @property
    def label(self) -> str:
        bits = [self.name]
        if self.region and self.region != self.name:
            bits.append(self.region)
        bits.append(self.country)
        return ", ".join(bits)


_ROWS = (
    ("London", "City of London, Greater London", "United Kingdom", 51.5074, -0.1278, "Europe/London", 0, 11.3, 7.0, 6.5, 75, 0.45, 16, 11, False),
    ("Manchester", "Manchester", "United Kingdom", 53.4808, -2.2426, "Europe/London", 0, 9.8, 6.6, 5.8, 79, 0.55, 18, 10, False),
    ("Edinburgh", "Edinburgh", "United Kingdom", 55.9533, -3.1883, "Europe/London", 0, 9.0, 6.2, 5.5, 80, 0.52, 21, 8, True),
    ("Dublin", "Dublin", "Ireland", 53.3498, -6.2603, "Europe/Dublin", 0, 9.8, 5.8, 5.4, 80, 0.50, 20, 9, True),
    ("Paris", "Ile-de-France", "France", 48.8566, 2.3522, "Europe/Paris", 1, 12.0, 8.4, 8.0, 72, 0.38, 14, 13, False),
    ("Berlin", "Berlin", "Germany", 52.5200, 13.4050, "Europe/Berlin", 1, 10.2, 10.0, 8.4, 71, 0.36, 15, 12, False),
    ("Amsterdam", "North Holland", "Netherlands", 52.3676, 4.9041, "Europe/Amsterdam", 1, 10.6, 7.6, 6.4, 78, 0.44, 19, 12, True),
    ("Madrid", "Madrid", "Spain", 40.4168, -3.7038, "Europe/Madrid", 1, 15.0, 10.4, 12.0, 55, 0.20, 12, 12, False),
    ("Barcelona", "Catalonia", "Spain", 41.3874, 2.1686, "Europe/Madrid", 1, 16.5, 8.2, 7.6, 70, 0.24, 13, 16, True),
    ("Lisbon", "Lisbon", "Portugal", 38.7223, -9.1393, "Europe/Lisbon", 0, 17.2, 6.8, 8.2, 71, 0.28, 17, 11, True),
    ("Rome", "Lazio", "Italy", 41.9028, 12.4964, "Europe/Rome", 1, 16.0, 8.8, 9.6, 68, 0.26, 12, 16, False),
    ("Athens", "Attica", "Greece", 37.9838, 23.7275, "Europe/Athens", 2, 18.8, 9.6, 9.0, 61, 0.18, 14, 17, True),
    ("Istanbul", "Istanbul", "Turkey", 41.0082, 28.9784, "Europe/Istanbul", 3, 14.6, 9.4, 7.4, 71, 0.32, 17, 21, True),
    ("Oslo", "Oslo", "Norway", 59.9139, 10.7522, "Europe/Oslo", 1, 6.3, 11.4, 8.0, 74, 0.40, 13, 7, True),
    ("Stockholm", "Stockholm", "Sweden", 59.3293, 18.0686, "Europe/Stockholm", 1, 7.4, 10.8, 7.2, 75, 0.38, 15, 6, True),
    ("Helsinki", "Uusimaa", "Finland", 60.1699, 24.9384, "Europe/Helsinki", 2, 6.0, 12.2, 7.0, 77, 0.40, 16, 6, True),
    ("Reykjavik", "Capital Region", "Iceland", 64.1466, -21.9426, "Atlantic/Reykjavik", 0, 5.0, 6.4, 4.8, 80, 0.58, 27, 4, True),
    ("Tromso", "Troms", "Norway", 69.6492, 18.9553, "Europe/Oslo", 1, 3.0, 9.8, 5.0, 78, 0.55, 20, 4, True),
    ("Moscow", "Moscow", "Russia", 55.7558, 37.6173, "Europe/Moscow", 3, 6.4, 14.6, 8.6, 74, 0.34, 14, 14, False),
    ("Warsaw", "Masovia", "Poland", 52.2297, 21.0122, "Europe/Warsaw", 1, 9.2, 11.6, 8.8, 73, 0.34, 14, 18, False),
    ("Zurich", "Zurich", "Switzerland", 47.3769, 8.5417, "Europe/Zurich", 1, 10.0, 9.6, 9.2, 74, 0.40, 10, 11, False),
    ("Cairo", "Cairo", "Egypt", 30.0444, 31.2357, "Africa/Cairo", 2, 22.4, 8.6, 12.4, 52, 0.03, 14, 42, False),
    ("Lagos", "Lagos", "Nigeria", 6.5244, 3.3792, "Africa/Lagos", 1, 27.2, 2.2, 7.2, 82, 0.44, 12, 45, True),
    ("Abuja", "Federal Capital Territory", "Nigeria", 9.0765, 7.3986, "Africa/Lagos", 1, 27.0, 3.0, 10.6, 66, 0.36, 11, 38, False),
    ("Accra", "Greater Accra", "Ghana", 5.6037, -0.1870, "Africa/Accra", 0, 27.0, 2.0, 6.8, 81, 0.34, 15, 40, True),
    ("Nairobi", "Nairobi", "Kenya", -1.2921, 36.8219, "Africa/Nairobi", 3, 18.6, 2.4, 11.0, 68, 0.30, 13, 24, False),
    ("Cape Town", "Western Cape", "South Africa", -33.9249, 18.4241, "Africa/Johannesburg", 2, 16.8, 6.0, 8.6, 71, 0.30, 24, 12, True),
    ("Johannesburg", "Gauteng", "South Africa", -26.2041, 28.0473, "Africa/Johannesburg", 2, 16.2, 6.6, 12.0, 58, 0.28, 14, 20, False),
    ("Casablanca", "Casablanca-Settat", "Morocco", 33.5731, -7.5898, "Africa/Casablanca", 1, 18.4, 6.0, 8.0, 74, 0.22, 18, 24, True),
    ("Dubai", "Dubai", "United Arab Emirates", 25.2048, 55.2708, "Asia/Dubai", 4, 28.0, 9.4, 10.4, 58, 0.03, 15, 48, True),
    ("Doha", "Doha", "Qatar", 25.2854, 51.5310, "Asia/Qatar", 3, 27.6, 10.0, 10.0, 56, 0.02, 16, 52, True),
    ("Riyadh", "Riyadh", "Saudi Arabia", 24.7136, 46.6753, "Asia/Riyadh", 3, 26.4, 11.4, 14.0, 30, 0.02, 14, 55, False),
    ("Tehran", "Tehran", "Iran", 35.6892, 51.3890, "Asia/Tehran", 3.5, 17.6, 12.4, 11.6, 40, 0.14, 13, 38, False),
    ("Karachi", "Sindh", "Pakistan", 24.8607, 67.0011, "Asia/Karachi", 5, 26.4, 6.4, 9.4, 66, 0.10, 15, 62, True),
    ("Delhi", "Delhi", "India", 28.6139, 77.2090, "Asia/Kolkata", 5.5, 25.4, 10.6, 12.4, 58, 0.20, 11, 92, False),
    ("Mumbai", "Maharashtra", "India", 19.0760, 72.8777, "Asia/Kolkata", 5.5, 27.4, 3.6, 7.0, 76, 0.30, 14, 58, True),
    ("Bengaluru", "Karnataka", "India", 12.9716, 77.5946, "Asia/Kolkata", 5.5, 24.2, 3.4, 10.6, 65, 0.26, 12, 44, False),
    ("Dhaka", "Dhaka", "Bangladesh", 23.8103, 90.4125, "Asia/Dhaka", 6, 26.2, 5.6, 9.2, 74, 0.34, 10, 78, False),
    ("Bangkok", "Bangkok", "Thailand", 13.7563, 100.5018, "Asia/Bangkok", 7, 28.6, 2.6, 8.6, 74, 0.34, 10, 34, False),
    ("Singapore", "Singapore", "Singapore", 1.3521, 103.8198, "Asia/Singapore", 8, 27.6, 1.0, 6.4, 82, 0.48, 9, 20, True),
    ("Jakarta", "Jakarta", "Indonesia", -6.2088, 106.8456, "Asia/Jakarta", 7, 27.8, 1.2, 7.4, 78, 0.44, 10, 42, True),
    ("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842, "Asia/Manila", 8, 28.0, 2.4, 7.4, 76, 0.42, 12, 36, True),
    ("Hong Kong", "Hong Kong", "Hong Kong", 22.3193, 114.1694, "Asia/Hong_Kong", 8, 23.6, 6.4, 5.4, 78, 0.36, 17, 28, True),
    ("Shanghai", "Shanghai", "China", 31.2304, 121.4737, "Asia/Shanghai", 8, 17.2, 11.0, 7.4, 74, 0.36, 14, 44, True),
    ("Beijing", "Beijing", "China", 39.9042, 116.4074, "Asia/Shanghai", 8, 13.0, 15.0, 10.4, 55, 0.22, 13, 58, False),
    ("Seoul", "Seoul", "South Korea", 37.5665, 126.9780, "Asia/Seoul", 9, 12.8, 14.4, 8.6, 64, 0.30, 12, 34, False),
    ("Tokyo", "Tokyo", "Japan", 35.6762, 139.6503, "Asia/Tokyo", 9, 16.4, 10.6, 6.6, 68, 0.36, 13, 18, True),
    ("Sydney", "New South Wales", "Australia", -33.8688, 151.2093, "Australia/Sydney", 10, 18.4, 5.4, 8.0, 68, 0.32, 16, 10, True),
    ("Melbourne", "Victoria", "Australia", -37.8136, 144.9631, "Australia/Melbourne", 10, 15.4, 6.2, 9.4, 66, 0.34, 18, 11, True),
    ("Perth", "Western Australia", "Australia", -31.9523, 115.8613, "Australia/Perth", 8, 18.8, 7.4, 11.4, 58, 0.22, 17, 10, True),
    ("Auckland", "Auckland", "New Zealand", -36.8485, 174.7633, "Pacific/Auckland", 12, 15.4, 4.6, 6.8, 78, 0.44, 20, 7, True),
    ("Honolulu", "Hawaii", "United States of America", 21.3069, -157.8583, "Pacific/Honolulu", -10, 25.4, 2.6, 6.0, 70, 0.28, 19, 8, True),
    ("Anchorage", "Alaska", "United States of America", 61.2181, -149.9003, "America/Anchorage", -9, 2.8, 14.0, 7.6, 72, 0.38, 12, 8, True),
    ("Vancouver", "British Columbia", "Canada", 49.2827, -123.1207, "America/Vancouver", -8, 11.0, 7.8, 6.6, 78, 0.48, 12, 8, True),
    ("Seattle", "Washington", "United States of America", 47.6062, -122.3321, "America/Los_Angeles", -8, 11.6, 7.8, 7.6, 76, 0.46, 12, 9, True),
    ("San Francisco", "California", "United States of America", 37.7749, -122.4194, "America/Los_Angeles", -8, 14.4, 3.4, 6.4, 74, 0.22, 18, 10, True),
    ("Los Angeles", "California", "United States of America", 34.0522, -118.2437, "America/Los_Angeles", -8, 18.6, 5.4, 9.4, 65, 0.10, 12, 22, True),
    ("Phoenix", "Arizona", "United States of America", 33.4484, -112.0740, "America/Phoenix", -7, 24.2, 11.4, 14.0, 33, 0.05, 12, 20, False),
    ("Denver", "Colorado", "United States of America", 39.7392, -104.9903, "America/Denver", -7, 10.6, 12.0, 13.4, 48, 0.20, 15, 12, False),
    ("Chicago", "Illinois", "United States of America", 41.8781, -87.6298, "America/Chicago", -6, 10.4, 14.6, 9.0, 70, 0.34, 18, 14, True),
    ("Toronto", "Ontario", "Canada", 43.6532, -79.3832, "America/Toronto", -5, 9.4, 14.2, 8.4, 71, 0.34, 17, 12, True),
    ("Montreal", "Quebec", "Canada", 45.5019, -73.5674, "America/Toronto", -5, 7.2, 15.6, 9.0, 72, 0.36, 16, 11, False),
    ("New York", "New York", "United States of America", 40.7128, -74.0060, "America/New_York", -5, 13.2, 12.6, 8.4, 66, 0.32, 16, 15, True),
    ("Washington", "District of Columbia", "United States of America", 38.9072, -77.0369, "America/New_York", -5, 15.0, 12.0, 9.6, 66, 0.30, 13, 15, False),
    ("Atlanta", "Georgia", "United States of America", 33.7490, -84.3880, "America/New_York", -5, 17.6, 9.8, 10.4, 68, 0.34, 12, 16, False),
    ("Miami", "Florida", "United States of America", 25.7617, -80.1918, "America/New_York", -5, 25.4, 4.8, 7.6, 74, 0.34, 15, 14, True),
    ("Mexico City", "Mexico City", "Mexico", 19.4326, -99.1332, "America/Mexico_City", -6, 17.0, 3.6, 13.4, 56, 0.28, 11, 34, False),
    ("Bogota", "Bogota", "Colombia", 4.7110, -74.0721, "America/Bogota", -5, 13.6, 1.4, 10.4, 74, 0.36, 11, 26, False),
    ("Lima", "Lima", "Peru", -12.0464, -77.0428, "America/Lima", -5, 19.2, 4.0, 6.0, 82, 0.06, 13, 32, True),
    ("Santiago", "Santiago", "Chile", -33.4489, -70.6693, "America/Santiago", -4, 14.6, 8.4, 13.6, 62, 0.16, 11, 30, False),
    ("Buenos Aires", "Buenos Aires", "Argentina", -34.6037, -58.3816, "America/Argentina/Buenos_Aires", -3, 17.6, 7.6, 9.4, 72, 0.30, 15, 20, True),
    ("Sao Paulo", "Sao Paulo", "Brazil", -23.5505, -46.6333, "America/Sao_Paulo", -3, 19.6, 4.2, 9.6, 76, 0.38, 12, 24, False),
    ("Rio de Janeiro", "Rio de Janeiro", "Brazil", -22.9068, -43.1729, "America/Sao_Paulo", -3, 23.8, 4.0, 7.4, 78, 0.32, 14, 22, True),
    ("Ushuaia", "Tierra del Fuego", "Argentina", -54.8019, -68.3030, "America/Argentina/Ushuaia", -3, 5.8, 6.2, 6.0, 76, 0.48, 26, 5, True),
    ("Nuuk", "Sermersooq", "Greenland", 64.1836, -51.7214, "America/Nuuk", -2, -0.6, 10.4, 5.0, 76, 0.42, 22, 4, True),
)

PLACES: tuple[Place, ...] = tuple(Place(*row) for row in _ROWS)
BY_KEY = {p.key: p for p in PLACES}


def lookup(query: str) -> Place | None:
    """Exact-ish lookup: name, 'name, country', or a unique prefix."""
    q = (query or "").strip().lower()
    if not q:
        return None
    if q in BY_KEY:
        return BY_KEY[q]
    head = q.split(",")[0].strip()
    if head in BY_KEY:
        return BY_KEY[head]
    prefixed = [p for p in PLACES if p.key.startswith(head)]
    if len(prefixed) == 1:
        return prefixed[0]
    contained = [p for p in PLACES if head in p.label.lower()]
    if contained:
        return contained[0]
    return prefixed[0] if prefixed else None


def search(query: str, limit: int = 8) -> list[dict]:
    """Ranked type-ahead: prefix matches first, then substring anywhere."""
    q = (query or "").strip().lower()
    if not q:
        return []
    scored = []
    for place in PLACES:
        label = place.label.lower()
        if place.key.startswith(q):
            rank = 0
        elif any(word.startswith(q) for word in label.replace(",", " ").split()):
            rank = 1
        elif q in label:
            rank = 2
        else:
            continue
        scored.append((rank, len(place.name), place))
    scored.sort(key=lambda item: (item[0], item[1], item[2].name))
    return [
        {
            "name": p.name,
            "region": p.region,
            "country": p.country,
            "lat": p.lat,
            "lon": p.lon,
            "tz_id": p.tz_id,
            "label": p.label,
        }
        for _, _, p in scored[:limit]
    ]
