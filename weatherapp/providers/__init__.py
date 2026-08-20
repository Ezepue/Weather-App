"""Provider adapters. Every one satisfies domain.WeatherProvider."""

from .caching import CachingProvider
from .demo import DemoProvider
from .factory import build_provider
from .weatherapi import WeatherAPIProvider

__all__ = ["CachingProvider", "DemoProvider", "WeatherAPIProvider", "build_provider"]
