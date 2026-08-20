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

PLACEHOLDERS = {
    "your_api_key_here", "your-api-key-here", "yourapikeyhere",
    "changeme", "xxx", "todo", "api_key", "none", "null",
}

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
    if value.lower() in PLACEHOLDERS:
        return Credential("", "placeholder",
                          "The key is still the placeholder from the setup instructions",
                          tuple(repaired))
    if not _EXPECTED_SHAPE.match(value.lower()):
        return Credential(
            value, "suspicious",
            f"Key is {len(value)} characters; WeatherAPI keys are 31-32 hex characters. "
            "It will still be tried.",
            tuple(repaired),
        )
    return Credential(value, "ok", "", tuple(repaired))
