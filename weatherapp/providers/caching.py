"""Caching as a decorator, so no provider contains a cache lookup.

Returns the same ProviderBundle type as the provider it wraps - a caller cannot
tell it apart from the real thing, which is the point.
"""

from __future__ import annotations

from dataclasses import replace

from ..domain.protocols import ProviderError


class CachingProvider:
    def __init__(self, inner, report_cache, search_cache=None):
        self._inner = inner
        self._reports = report_cache
        self._searches = search_cache
        self.name = inner.name

    def fetch(self, query: str, days: int = 3):
        key = self._key(query, days)
        hit = self._reports.get(key)
        if hit is not None:
            bundle, age = hit
            return replace(bundle, cached=True, age_seconds=round(age, 1), stale=False)

        try:
            bundle = self._inner.fetch(query, days)
        except ProviderError:
            # A stale answer beats an error page when the upstream is down.
            fallback = self._reports.get(key, allow_stale=True)
            if fallback is None:
                raise
            bundle, age = fallback
            return replace(
                bundle,
                cached=True,
                age_seconds=round(age, 1),
                stale=True,
                notices=[*bundle.notices, f"Live update failed; showing data from {int(age // 60)} min ago."],
            )

        self._reports.set(key, bundle)
        return replace(bundle, cached=False, age_seconds=0.0, stale=False)

    def search(self, query: str, limit: int = 8) -> list[dict]:
        if self._searches is None:
            return self._inner.search(query, limit)
        key = f"search:{self.name}:{(query or '').strip().lower()}:{limit}"
        hit = self._searches.get(key)
        if hit is not None:
            return hit[0]
        rows = self._inner.search(query, limit)
        self._searches.set(key, rows)
        return rows

    def invalidate(self, query: str | None = None, days: int = 3) -> None:
        self._reports.invalidate(None if query is None else self._key(query, days))

    def stats(self) -> dict:
        return self._reports.stats()

    def _key(self, query: str, days: int) -> str:
        return f"report:{self.name}:{(query or '').strip().lower()}:{days}"
