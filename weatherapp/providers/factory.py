"""One place decides which provider the application runs on."""

from __future__ import annotations

from ..infrastructure.cache import TTLCache
from ..infrastructure.http import HttpClient
from .caching import CachingProvider
from .demo import DemoProvider
from .weatherapi import WeatherAPIProvider


def build_provider(settings, clock, http=None):
    """Live provider when a key is configured, demo otherwise; always cached."""
    if settings.live:
        inner = WeatherAPIProvider(
            http=http or HttpClient(timeout=settings.http_timeout),
            api_key=settings.api_key,
            base_url=settings.base_url,
            marine_enabled=settings.marine_enabled,
        )
    else:
        inner = DemoProvider(clock=clock, default_place=settings.default_place)

    return CachingProvider(
        inner,
        report_cache=TTLCache(
            ttl=settings.cache_ttl,
            stale_ttl=settings.cache_stale_ttl,
            max_entries=settings.cache_max_entries,
        ),
        search_cache=TTLCache(ttl=600.0, stale_ttl=1800.0, max_entries=512),
    )
