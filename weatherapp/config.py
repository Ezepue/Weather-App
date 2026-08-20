"""Runtime configuration for Barograph.

Everything is environment driven so the same code runs locally, on Vercel and
in CI.  The only genuinely required variable is ``API_KEY``; without it the app
falls back to the deterministic demo provider instead of erroring out.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _num(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """Immutable-ish snapshot of the process configuration."""

    api_key: str = ""
    provider: str = "auto"          # auto | weatherapi | demo
    base_url: str = "https://api.weatherapi.com/v1/"
    default_place: str = "London"
    forecast_days: int = 3          # WeatherAPI free tier ceiling
    cache_ttl: float = 300.0        # seconds a report stays fresh
    cache_stale_ttl: float = 3600.0  # seconds a stale report may still be served
    cache_max_entries: int = 256
    http_timeout: float = 8.0
    time_quantum: int = 60      # 'now' is bucketed so ETags stay stable
    marine_enabled: bool = True
    version: str = "2.0.0"
    build: str = field(default_factory=lambda: os.getenv("BUILD_ID", "dev"))

    @classmethod
    def from_env(cls) -> "Settings":
        key = (os.getenv("API_KEY") or os.getenv("WEATHERAPI_KEY") or "").strip()
        provider = (os.getenv("WEATHER_PROVIDER") or "auto").strip().lower()
        if provider not in {"auto", "weatherapi", "demo"}:
            provider = "auto"
        return cls(
            api_key=key,
            provider=provider,
            base_url=os.getenv("WEATHER_BASE_URL", "https://api.weatherapi.com/v1/"),
            default_place=os.getenv("DEFAULT_PLACE", "London"),
            forecast_days=int(_num("FORECAST_DAYS", 3)),
            cache_ttl=_num("CACHE_TTL", 300.0),
            cache_stale_ttl=_num("CACHE_STALE_TTL", 3600.0),
            http_timeout=_num("HTTP_TIMEOUT", 8.0),
            time_quantum=int(_num("TIME_QUANTUM", 60)),
            marine_enabled=_flag("MARINE_ENABLED", True),
        )

    @property
    def live(self) -> bool:
        """True when we should talk to the real upstream API."""
        if self.provider == "demo":
            return False
        if self.provider == "weatherapi":
            return True
        return bool(self.api_key)

    @property
    def active_provider(self) -> str:
        return "weatherapi" if self.live else "demo"
