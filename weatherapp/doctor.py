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
    return _probe(settings, credential.value)


def _probe(settings, key: str) -> int:
    """Try each endpoint over both schemes.

    A free WeatherAPI plan serves HTTP only and answers an HTTPS request by
    rejecting the key, so "invalid key" and "no TLS on this plan" are
    indistinguishable from a single request. Two schemes tell them apart.
    """
    http = HttpClient(timeout=settings.http_timeout, retries=0)
    endpoints = (
        ("current.json", {"q": "London", "aqi": "yes"}),
        ("forecast.json", {"q": "London", "days": settings.forecast_days,
                           "aqi": "yes", "alerts": "yes"}),
        ("search.json", {"q": "lond"}),
    )
    if settings.marine_enabled:
        endpoints += (("marine.json", {"q": "Brighton", "days": 1}),)

    host = settings.base_url.split("://", 1)[-1].rstrip("/")
    results: dict[str, dict] = {}

    for scheme in ("https", "http"):
        print(f"\n  {scheme.upper()}")
        results[scheme] = {}
        for path, params in endpoints:
            try:
                payload = http.get_json(f"{scheme}://{host}/{path}", {"key": key, **params})
            except ProviderError as exc:
                results[scheme][path] = f"unreachable ({exc})"
                _line(CROSS, f"  {path:14} {exc}")
                continue
            error = (payload or {}).get("error") or {}
            if error:
                results[scheme][path] = f"code {error.get('code')}"
                _line(CROSS, f"  {path:14} code {error.get('code')}: {error.get('message')}")
            else:
                results[scheme][path] = "ok"
                _line(TICK, f"  {path:14} ok")

    print("\n" + "-" * 52)
    https_ok = [p for p, r in results["https"].items() if r == "ok"]
    http_ok = [p for p, r in results["http"].items() if r == "ok"]

    if https_ok:
        _line(TICK, "the key works over HTTPS - nothing to change")
        return 0
    if http_ok:
        _line(WARN, "the key works over HTTP but not HTTPS")
        _line(INFO, "this plan does not include TLS. The app already retries over")
        _line(INFO, "HTTP automatically, so it will work - but the key travels in")
        _line(INFO, "cleartext. To make it explicit and skip the failed attempt:")
        _line(INFO, "  WEATHER_BASE_URL=http://api.weatherapi.com/v1/")
        _line(INFO, "Set ALLOW_HTTP_FALLBACK=0 to refuse cleartext instead.")
        return 0
    codes = {r for r in list(results["https"].values()) + list(results["http"].values())}
    if any("2006" in c for c in codes):
        _line(CROSS, "rejected over both schemes: the key itself is not valid")
        _line(INFO, "re-copy it from weatherapi.com/my-account. New keys take a few")
        _line(INFO, "minutes to activate; trial keys expire after 14 days.")
    elif any("unreachable" in c for c in codes):
        _line(CROSS, "could not reach the API at all - check network or proxy")
    else:
        _line(CROSS, f"no endpoint succeeded: {sorted(codes)}")
    return 1


if __name__ == "__main__":
    sys.exit(run())
