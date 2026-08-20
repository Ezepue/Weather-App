"""Key diagnosis for a local checkout: python -m weatherapp.doctor

A terminal rendering of weatherapp.diagnostics. The deployed equivalent is
GET /api/v1/diagnose, which runs the same code.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import PROJECT_ROOT, load_environment
from .config import Settings
from .diagnostics import diagnose

TICK, CROSS, WARN, INFO = "  ok  ", " FAIL ", " warn ", " ---- "
_MARKS = {"ok": TICK, "rejected": CROSS, "unreachable": CROSS}


def _line(mark: str, text: str) -> None:
    print(f"[{mark}] {text}")


def run(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # Probing over HTTP puts the key in a cleartext URL, so it is never done
    # unless the operator asks for it.
    insecure = "--insecure-probe" in argv
    schemes = ("https", "http") if insecure else ("https",)

    print("Barograph key diagnosis\n" + "=" * 58)
    if insecure:
        _line(WARN, "--insecure-probe: HTTP attempts will send the key in cleartext")

    env_file = load_environment()
    if env_file:
        _line(TICK, f".env found at {env_file}")
    else:
        _line(WARN, f"no .env at {PROJECT_ROOT / '.env'}")

    local_env = Path.cwd() / ".env"
    if local_env.is_file() and local_env.resolve() != (PROJECT_ROOT / ".env").resolve():
        _line(WARN, f"a second .env exists at {local_env}")
        _line(INFO, "the previous version read that one; this version reads the")
        _line(INFO, "project root. Different keys in the two is exactly this bug.")

    raw, source = None, ""
    for name in ("API_KEY", "WEATHERAPI_KEY"):
        if os.getenv(name) is not None:
            raw, source = os.getenv(name), name
            break
    if source == "":
        _line(CROSS, "neither API_KEY nor WEATHERAPI_KEY is set")
        _line(INFO, f"fix: echo 'API_KEY=your_key' > {PROJECT_ROOT / '.env'}")
        return 1

    report = diagnose(Settings.from_env(), raw, source, schemes=schemes)
    key = report["key"]
    _line(INFO, f"source            {key['source']}")
    _line(INFO, f"value             {key['masked']} ({key['length']} chars)")
    _line(INFO, f"charset           {key['charset']}")
    if key["normalised"]:
        _line(WARN, f"normalised        {', '.join(key['normalised'])}")
    _line(INFO, f"base url          {report['base_url']}")

    if report["probes"]:
        print("-" * 58)
        for entry in report["probes"]:
            tag = f"{entry['scheme']:5} {entry['style']:6} {entry['value']:10}"
            _line(_MARKS.get(entry["outcome"], WARN), f"{tag} {entry.get('detail', '')}")

    print("-" * 58)
    result = report["verdict"]
    if result["state"] != "ok" and not insecure:
        _line(INFO, "if the plan may lack TLS, re-run with --insecure-probe to test")
        _line(INFO, "HTTP as well (this sends the key unencrypted)")
    _line(TICK if result["state"] == "ok" else CROSS, result["headline"])
    for sentence in str(result.get("detail", "")).split(". "):
        if sentence.strip():
            _line(INFO, f"  {sentence.strip().rstrip('.')}.")
    return 0 if result["state"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(run())
