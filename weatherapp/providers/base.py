from __future__ import annotations

import hashlib


def stable_seed(*parts: object) -> int:
    """Python's hash() is salted per process, so demo data would not be stable."""
    joined = "|".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(joined.encode("utf-8")).digest()[:8], "big")


def parse_latlon(query: str) -> tuple[float, float] | None:
    if "," not in (query or ""):
        return None
    left, _, right = query.partition(",")
    try:
        lat, lon = float(left.strip()), float(right.strip())
    except ValueError:
        return None
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None
