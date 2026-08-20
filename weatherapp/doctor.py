"""Key and connectivity diagnosis: python -m weatherapp.doctor

Prints where the key came from, what it looks like after normalisation, and
what WeatherAPI says about it. The key itself is always masked so the output
is safe to paste into an issue.
"""

from __future__ import annotations

import os
import re
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

    from pathlib import Path
    local_env = Path.cwd() / ".env"
    if local_env.is_file() and local_env.resolve() != (PROJECT_ROOT / ".env").resolve():
        _line(WARN, f"a second .env exists at {local_env}")
        _line(INFO, "the previous version read that one; this version reads the")
        _line(INFO, "project-root file. If they hold different keys, that is the bug.")

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
    return _probe(settings, credential.value, os.getenv(present[0]))


def _charset(value: str) -> str:
    """Describe the key's characters without printing them."""
    bits = []
    if re.fullmatch(r"[0-9a-f]+", value):
        bits.append("lowercase hex")
    elif re.fullmatch(r"[0-9A-Za-z]+", value):
        bits.append("alphanumeric")
    else:
        odd = sorted({c for c in value if not c.isalnum()})
        bits.append("contains " + " ".join(repr(c) for c in odd))
    if any(c.isupper() for c in value):
        bits.append("has uppercase")
    return ", ".join(bits)


def _probe(settings, key: str, raw: str) -> int:
    """Isolate every difference between this code and the version that worked.

    The old app interpolated the key into the URL over HTTP with no
    normalisation. This one normalises, passes params= and prefers HTTPS. Each
    of those is a suspect until a probe clears it, so all combinations are
    tried rather than reasoned about.
    """
    http = HttpClient(timeout=settings.http_timeout, retries=0)
    host = settings.base_url.split("://", 1)[-1].rstrip("/")

    values = [("normalised", key)]
    if raw is not None and raw.strip() != key:
        values.append(("raw env value", raw.strip()))

    _line(INFO, f"charset           {_charset(key)}")
    print()

    winners = []
    answered = []          # probes that got a real reply, refused or not
    for scheme in ("https", "http"):
        for label, value in values:
            for style in ("params", "inline"):
                url = f"{scheme}://{host}/current.json"
                if style == "inline":
                    # Exactly how the previous version built it.
                    url = f"{url}?key={value}&q=London&aqi=yes"
                    params = None
                else:
                    params = {"key": value, "q": "London", "aqi": "yes"}
                tag = f"{scheme:5} {style:6} {label}"
                try:
                    payload = http.get_json(url, params)
                except ProviderError as exc:
                    _line(CROSS, f"{tag:38} {exc}")
                    continue
                error = (payload or {}).get("error") or {}
                if error:
                    answered.append(error.get("code"))
                    _line(CROSS, f"{tag:38} code {error.get('code')}: {error.get('message')}")
                else:
                    answered.append(None)
                    _line(TICK, f"{tag:38} ok")
                    winners.append((scheme, style, label))

    print("\n" + "-" * 52)
    if not winners and not answered:
        # Nothing replied, so nothing was learned about the key.
        _line(CROSS, "no probe reached WeatherAPI - this is a network or proxy")
        _line(INFO, "problem, not a key problem. Nothing here judges the key.")
        return 1
    if not winners:
        _line(CROSS, f"every combination was rejected (codes {sorted({c for c in answered if c})})")
        _line(INFO, "the key itself is not accepted by WeatherAPI. Compare the")
        _line(INFO, "masked value above against weatherapi.com/my-account - if the")
        _line(INFO, "first and last four characters differ, the app is reading a")
        _line(INFO, "different key than you think (check for a second .env).")
        return 1

    schemes = {w[0] for w in winners}
    styles = {w[1] for w in winners}
    labels = {w[2] for w in winners}

    _line(TICK, f"working combinations: {len(winners)}")
    if "https" not in schemes:
        _line(WARN, "HTTPS never works: this plan has no TLS")
        _line(INFO, "set WEATHER_BASE_URL=http://api.weatherapi.com/v1/")
    if "params" not in styles:
        _line(WARN, "only the inline-URL form works, which means the key contains")
        _line(INFO, "characters that must not be percent-encoded. Report this - the")
        _line(INFO, "adapter needs to build that URL by hand.")
    if "normalised" not in labels:
        _line(CROSS, "only the RAW value works - normalisation is corrupting the key")
        _line(INFO, "set the key exactly, with no quotes or prefix, and report this.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
