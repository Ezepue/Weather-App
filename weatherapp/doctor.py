"""Key and connectivity diagnosis: python -m weatherapp.doctor

Prints where the key came from, what it looks like after normalisation, and
what WeatherAPI says about it. The key itself is always masked so the output
is safe to paste into an issue.
"""

from __future__ import annotations

import os
import sys

from . import PROJECT_ROOT, load_environment
from .config import Settings
from .domain.protocols import ProviderError
from .infrastructure.credentials import sanitize
from .infrastructure.http import HttpClient

TICK, CROSS, WARN, INFO = "  ok  ", " FAIL ", " warn ", " ---- "


def _line(mark: str, text: str) -> None:
    print(f"[{mark}] {text}")


def run() -> int:
    print("Barograph key diagnosis\n" + "=" * 52)

    env_file = load_environment()
    if env_file:
        _line(TICK, f".env found at {env_file}")
    else:
        _line(WARN, f"no .env at {PROJECT_ROOT / '.env'} - relying on the process environment")

    present = [name for name in ("API_KEY", "WEATHERAPI_KEY") if os.getenv(name) is not None]
    if not present:
        _line(CROSS, "neither API_KEY nor WEATHERAPI_KEY is set")
        _line(INFO, f"fix: echo 'API_KEY=your_key' > {PROJECT_ROOT / '.env'}")
        _line(INFO, "the app is serving demo data until then, which is why it still loads")
        return 1
    if len(present) > 1:
        _line(WARN, f"both {' and '.join(present)} are set; API_KEY wins")

    settings = Settings.from_env()
    credential = sanitize(os.getenv(present[0]))

    _line(INFO, f"source            {present[0]}")
    _line(INFO, f"value             {credential.masked()} ({len(credential.value)} chars)")
    if credential.repaired:
        _line(WARN, f"normalised        {', '.join(credential.repaired)}")
        _line(INFO, "                  the raw value was not a bare key; check the .env line")

    if credential.status == "placeholder":
        _line(CROSS, "the key is still the placeholder from the setup instructions")
        _line(INFO, "fix: replace it with a real key from weatherapi.com/my-account")
        return 1
    if credential.status == "missing":
        _line(CROSS, "the variable is set but empty")
        return 1
    if credential.status == "suspicious":
        _line(WARN, credential.note)
    else:
        _line(TICK, "shape looks like a WeatherAPI key (32 hex characters)")

    if not settings.live:
        _line(CROSS, f"provider resolved to '{settings.active_provider}' - WEATHER_PROVIDER={os.getenv('WEATHER_PROVIDER')}")
        return 1

    print("-" * 52)
    _line(INFO, f"probing {settings.base_url}current.json ...")
    http = HttpClient(timeout=settings.http_timeout, retries=0)
    from .providers.weatherapi import WeatherAPIProvider

    provider = WeatherAPIProvider(
        http=http, api_key=credential.value,
        base_url=settings.base_url, marine_enabled=False,
    )
    try:
        report = provider.fetch("London", days=1)
    except ProviderError as exc:
        _line(CROSS, f"upstream refused (HTTP {exc.status}, {exc.kind})")
        for chunk in str(exc).split(". "):
            if chunk.strip():
                _line(INFO, f"  {chunk.strip().rstrip('.')}.")
        return 1
    except Exception as exc:  # noqa: BLE001 - a diagnostic must report, not crash
        _line(CROSS, f"unexpected failure: {type(exc).__name__}: {exc}")
        return 1

    _line(TICK, f"live data received: {report.place.name}, {report.current.temp_c}C")
    _line(TICK, "the key works - the app will serve live weather")

    if settings.marine_enabled:
        marine_provider = WeatherAPIProvider(
            http=http, api_key=credential.value,
            base_url=settings.base_url, marine_enabled=True,
        )
        _, notice = marine_provider._marine("London", 0)
        if notice:
            _line(WARN, f"marine: {notice}")
        else:
            _line(INFO, "marine endpoint reachable or cleanly skipped")
    return 0


if __name__ == "__main__":
    sys.exit(run())
