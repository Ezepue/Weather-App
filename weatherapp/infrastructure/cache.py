"""A small thread-safe TTL cache.

WeatherAPI's free tier is metered, so every report is cached.  The cache also
keeps entries past their freshness deadline: if the upstream call later fails,
a stale-but-labelled report is far more useful to a person than an error page.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class Entry:
    value: Any
    stored_at: float

    def age(self, now: float | None = None) -> float:
        return (now or time.time()) - self.stored_at


class TTLCache:
    def __init__(self, ttl: float = 300.0, stale_ttl: float = 3600.0, max_entries: int = 256):
        self.ttl = ttl
        self.stale_ttl = stale_ttl
        self.max_entries = max_entries
        self._data: "OrderedDict[str, Entry]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.stale_serves = 0

    def get(self, key: str, allow_stale: bool = False) -> tuple[Any, float] | None:
        """Return ``(value, age_seconds)`` or None."""
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            age = entry.age(now)
            limit = self.stale_ttl if allow_stale else self.ttl
            if age > limit:
                if age > self.stale_ttl:
                    self._data.pop(key, None)
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            if age > self.ttl:
                self.stale_serves += 1
            return entry.value, age

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = Entry(value=value, stored_at=time.time())
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def invalidate(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._data.clear()
            else:
                self._data.pop(key, None)

    def stats(self) -> dict:
        with self._lock:
            return {
                "entries": len(self._data),
                "hits": self.hits,
                "misses": self.misses,
                "stale_serves": self.stale_serves,
                "ttl": self.ttl,
                "stale_ttl": self.stale_ttl,
            }
