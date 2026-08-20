"""The contracts that let layers depend on each other without knowing each other."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Upstream failed. Carries the status the API layer should return."""

    def __init__(self, message: str, status: int = 502, kind: str = "upstream"):
        super().__init__(message)
        self.status = status
        self.kind = kind


@runtime_checkable
class WeatherProvider(Protocol):
    """Two methods, so a caller that only searches need not depend on fetching."""

    name: str

    def fetch(self, query: str, days: int = 3) -> "object":
        """Return a ProviderBundle. Raise ProviderError on failure."""

    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Return place suggestions. Must not raise for an empty query."""


@runtime_checkable
class Clock(Protocol):
    """Time as an injected dependency, so tests are not racing the wall clock."""

    def now(self) -> datetime: ...

    def epoch(self) -> int: ...


@runtime_checkable
class Scorer(Protocol):
    """A strategy that judges one activity against one advice.Snapshot.

    Uniform signature is what lets the registry list, filter and test scorers
    without knowing which fields any individual one reads.
    """

    key: str
    label: str

    def __call__(self, snapshot: object) -> dict: ...
