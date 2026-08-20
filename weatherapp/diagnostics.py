"""Key diagnosis as data.

The terminal command and the HTTP endpoint are two renderings of this one
function, so a deployed instance and a laptop cannot disagree about what is
wrong.
"""

from __future__ import annotations

import re

from .domain.protocols import ProviderError
from .infrastructure.credentials import sanitize
from .infrastructure.http import HttpClient

SCHEMES = ("https", "http")
STYLES = ("params", "inline")


def charset(value: str) -> str:
    """Describe the key's characters without revealing them."""
    if not value:
        return "empty"
    if re.fullmatch(r"[0-9a-f]+", value):
        description = "lowercase hex"
    elif re.fullmatch(r"[0-9A-Za-z]+", value):
        description = "alphanumeric"
    else:
        odd = sorted({c for c in value if not c.isalnum()})
        description = "contains " + " ".join(repr(c) for c in odd)
    if any(c.isupper() for c in value):
        description += ", has uppercase"
    return description


def probe(settings, key: str, raw: str | None, http=None) -> list[dict]:
    """Try every combination of the things this rewrite changed.

    The previous version interpolated the key into an HTTP URL with no
    normalisation. Each difference is a suspect until a probe clears it.
    """
    http = http or HttpClient(timeout=settings.http_timeout, retries=0)
    host = settings.base_url.split("://", 1)[-1].rstrip("/")

    values = [("normalised", key)]
    if raw is not None and raw.strip() and raw.strip() != key:
        values.append(("raw", raw.strip()))

    results = []
    for scheme in SCHEMES:
        for label, value in values:
            for style in STYLES:
                url = f"{scheme}://{host}/current.json"
                if style == "inline":
                    params = None
                    url = f"{url}?key={value}&q=London&aqi=yes"
                else:
                    params = {"key": value, "q": "London", "aqi": "yes"}

                entry = {"scheme": scheme, "style": style, "value": label}
                try:
                    payload = http.get_json(url, params)
                except ProviderError as exc:
                    entry.update(outcome="unreachable", detail=str(exc))
                else:
                    error = (payload or {}).get("error") or {}
                    if error:
                        entry.update(outcome="rejected", code=error.get("code"),
                                     detail=error.get("message"))
                    else:
                        entry.update(outcome="ok", detail="accepted")
                results.append(entry)
    return results


def verdict(results: list[dict]) -> dict:
    """Turn the matrix into one conclusion and one instruction."""
    winners = [r for r in results if r["outcome"] == "ok"]
    answered = [r for r in results if r["outcome"] == "rejected"]

    if not winners and not answered:
        return {
            "state": "unreachable",
            "headline": "No probe reached WeatherAPI",
            "detail": "This is a network or proxy problem. Nothing here judges the key.",
        }
    if not winners:
        codes = sorted({r.get("code") for r in answered if r.get("code")})
        return {
            "state": "rejected",
            "headline": "Every combination was rejected",
            "detail": f"WeatherAPI refused the key in all forms (codes {codes}). "
                      "Compare the masked value against weatherapi.com/my-account; "
                      "if the first or last four characters differ, this instance is "
                      "reading a different key than you expect.",
            "codes": codes,
        }

    schemes = {r["scheme"] for r in winners}
    styles = {r["style"] for r in winners}
    values = {r["value"] for r in winners}
    notes = []
    if "https" not in schemes:
        notes.append("HTTPS never works: this plan has no TLS. "
                     "Set WEATHER_BASE_URL=http://api.weatherapi.com/v1/")
    if "params" not in styles:
        notes.append("Only the inline URL form works: the key contains characters "
                     "that must not be percent-encoded. The adapter must build the "
                     "URL by hand.")
    if "normalised" not in values:
        notes.append("Only the raw value works: normalisation is corrupting the key.")
    return {
        "state": "ok",
        "headline": f"{len(winners)} working combination(s)",
        "detail": " ".join(notes) or "The key works as configured.",
        "notes": notes,
    }


def diagnose(settings, raw_key: str | None, source: str, http=None) -> dict:
    credential = sanitize(raw_key)
    report = {
        "provider": settings.active_provider,
        "base_url": settings.base_url,
        "key": {
            "source": source or None,
            "status": credential.status,
            "masked": credential.masked(),
            "length": len(credential.value),
            "charset": charset(credential.value),
            "normalised": list(credential.repaired),
        },
        "probes": [],
        "verdict": {},
    }
    if not credential.usable:
        report["verdict"] = {
            "state": credential.status,
            "headline": credential.note or "No usable key configured",
            "detail": "Nothing was probed because there is no key to probe.",
        }
        return report

    report["probes"] = probe(settings, credential.value, raw_key, http=http)
    report["verdict"] = verdict(report["probes"])
    return report
