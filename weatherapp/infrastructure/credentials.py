"""Reading an API key from a human-edited file, forgivingly.

Almost every "API key is invalid" report is a transport problem rather than a
wrong key: a pasted `API_KEY=...` line, smart quotes from a text editor, a
trailing CR from a Windows file, or the whole dashboard URL. Normalising here
means the adapter can assume the key is a key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

# An enumerated list only catches the spellings someone thought of; the real
# world supplies "your_secret_key", "REPLACE-ME", "insert api key" and so on.
# Match the shape of a placeholder instead: an English instruction rather than
# a credential. A real key is hex or alphanumeric and matches none of these.
_PLACEHOLDER_PATTERNS = (
    r"(your|my|the|our)[\W_]*(own)?[\W_]*(api|secret|access|private)?[\W_]*(key|secret|token|value|here)",
    r"(insert|enter|put|add|paste|replace|set)[\W_]*(your)?[\W_]*(api|secret)?[\W_]*(key|token|here|me)",
    r"^(changeme|change[\W_]*me|replaceme|todo|tbd|fixme|xxx+|none|null|undefined|empty)$",
    r"^(api|secret|access)[\W_]*(key|token)$",
    r"^(example|sample|test|dummy|fake|placeholder|abc123|foobar)[\W_]*(key|token)?$",
    r"<.*>",          # <your key here>
    r"^\.\.\.+$",
)

# WeatherAPI issues 31-32 hex characters. Shape is advisory: the format is
# theirs to change, so a mismatch warns rather than blocks.
_EXPECTED_SHAPE = re.compile(r"^[0-9a-f]{31,32}$")
_QUOTES = "\"'‘’“”«»`"


@dataclass(frozen=True)
class Credential:
    value: str
    status: str          # ok | missing | placeholder | suspicious
    note: str = ""
    repaired: tuple = ()

    @property
    def usable(self) -> bool:
        return self.status in {"ok", "suspicious"} and bool(self.value)

    def masked(self) -> str:
        if not self.value:
            return "(none)"
        if len(self.value) <= 8:
            return "*" * len(self.value)
        return f"{self.value[:4]}{'*' * (len(self.value) - 8)}{self.value[-4:]}"


def looks_like_placeholder(value: str) -> bool:
    """True when the value reads as instructions rather than a credential."""
    candidate = value.strip().lower()
    if not candidate:
        return False
    return any(re.search(pattern, candidate) for pattern in _PLACEHOLDER_PATTERNS)


def sanitize(raw: str | None) -> Credential:
    if raw is None:
        return Credential("", "missing", "No key supplied")

    value = raw
    repaired: list[str] = []

    stripped = value.strip().strip("\r\n\t ")
    if stripped != value:
        repaired.append("trimmed whitespace")
    value = stripped

    while len(value) >= 2 and value[0] in _QUOTES and value[-1] in _QUOTES:
        value = value[1:-1].strip()
        repaired.append("removed surrounding quotes")

    # A whole request URL copied out of the dashboard: take its key parameter.
    if "://" in value or value.lower().startswith("api."):
        found = parse_qs(urlparse(value if "://" in value else "https://" + value).query).get("key")
        if found and found[0].strip():
            value = found[0].strip()
            repaired.append("extracted the key parameter from a URL")

    # A pasted dotenv line: API_KEY=..., key=..., WEATHERAPI_KEY=...
    if "=" in value:
        head, _, tail = value.partition("=")
        if re.fullmatch(r"\s*[A-Za-z0-9_\-]*(key)\s*", head, re.IGNORECASE) and tail.strip():
            value = tail.strip().strip(_QUOTES).strip()
            repaired.append("stripped a key= prefix")

    if "&" in value:
        value = value.split("&", 1)[0].strip()
        repaired.append("dropped trailing URL parameters")

    value = value.strip().strip(_QUOTES).strip()

    if not value:
        return Credential("", "missing", "No key supplied", tuple(repaired))
    if looks_like_placeholder(value):
        return Credential("", "placeholder",
                          "API_KEY is still the placeholder from the setup "
                          "instructions. Replace it with a real key.",
                          tuple(repaired))
    if not _EXPECTED_SHAPE.match(value.lower()):
        return Credential(
            value, "suspicious",
            f"Key is {len(value)} characters; WeatherAPI keys are 31-32 hex characters. "
            "It will still be tried.",
            tuple(repaired),
        )
    return Credential(value, "ok", "", tuple(repaired))
