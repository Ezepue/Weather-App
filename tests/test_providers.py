"""Providers must be interchangeable, and the demo one must be deterministic."""


from datetime import datetime, timezone

import pytest

from weatherapp.domain import ProviderBundle, WeatherProvider
from weatherapp.domain.protocols import ProviderError
from weatherapp.infrastructure.cache import TTLCache
from weatherapp.infrastructure.clock import FrozenClock
from weatherapp.providers.base import parse_latlon, stable_seed
from weatherapp.providers.caching import CachingProvider
from weatherapp.providers.demo import DemoProvider
from weatherapp.providers.weatherapi import WeatherAPIProvider


class TestBaseHelpers:
    @pytest.mark.parametrize("text,expected", [
        ("51.5,-0.12", (51.5, -0.12)),
        (" -33.87 , 151.21 ", (-33.87, 151.21)),
        ("0,0", (0.0, 0.0)),
    ])
    def test_parses_coordinates(self, text, expected):
        assert parse_latlon(text) == expected

    @pytest.mark.parametrize("text", ["London", "", "91,0", "0,181", "abc,def", "1"])
    def test_rejects_non_coordinates(self, text):
        assert parse_latlon(text) is None

    def test_seed_is_stable_across_calls(self):
        assert stable_seed("London", 1) == stable_seed("London", 1)
        assert stable_seed("London") != stable_seed("Paris")


class TestDemoProvider:
    def test_satisfies_the_protocol(self, provider):
        assert isinstance(provider, WeatherProvider)

    def test_returns_a_bundle(self, provider):
        assert isinstance(provider.fetch("London"), ProviderBundle)

    def test_is_deterministic(self, clock):
        a = DemoProvider(clock).fetch("London", 3)
        b = DemoProvider(clock).fetch("London", 3)
        assert a.current.temp_c == b.current.temp_c
        assert [h.temp_c for h in a.hourly] == [h.temp_c for h in b.hourly]

    def test_different_places_differ(self, provider):
        assert provider.fetch("London").current.temp_c != provider.fetch("Cairo").current.temp_c

    def test_hour_and_day_counts(self, provider):
        bundle = provider.fetch("London", 3)
        assert len(bundle.hourly) == 72
        assert len(bundle.daily) == 3

    def test_respects_requested_days(self, provider):
        assert len(provider.fetch("London", 5).daily) == 5

    def test_physical_consistency(self, provider):
        bundle = provider.fetch("Singapore", 3)
        for hour in bundle.hourly:
            assert -95 <= hour.temp_c <= 65
            assert 0 <= hour.humidity <= 100
            assert hour.dewpoint_c <= hour.temp_c + 0.01, "dew point cannot exceed air temperature"
            assert 0 <= hour.cloud <= 100
            assert 0 <= hour.uv <= 13
            assert hour.precip_mm >= 0
            assert 850 <= hour.pressure_mb <= 1090
            assert 0 <= hour.wind_dir_deg < 360
            assert hour.gust_kph >= hour.wind_kph

    def test_uv_is_zero_at_night(self, provider):
        bundle = provider.fetch("London", 2)
        for hour in bundle.hourly:
            if not hour.is_day:
                assert hour.uv == 0

    def test_daily_aggregates_bound_the_hours(self, provider):
        bundle = provider.fetch("Chicago", 3)
        for index, day in enumerate(bundle.daily):
            hours = bundle.hourly[index * 24:(index + 1) * 24]
            assert day.maxtemp_c == pytest.approx(max(h.temp_c for h in hours))
            assert day.mintemp_c == pytest.approx(min(h.temp_c for h in hours))
            assert day.mintemp_c <= day.avgtemp_c <= day.maxtemp_c

    def test_seasons_are_the_right_way_round(self):
        def temp(city, month):
            clock = FrozenClock(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
            return DemoProvider(clock).fetch(city, 1).daily[0].avgtemp_c

        assert temp("London", 7) > temp("London", 1), "northern summer must be warmer"
        assert temp("Sydney", 1) > temp("Sydney", 7), "southern hemisphere must be inverted"

    def test_polar_night_has_no_daylight(self):
        clock = FrozenClock(datetime(2026, 12, 21, 12, tzinfo=timezone.utc))
        assert DemoProvider(clock).fetch("Tromso", 1).daily[0].daylight_minutes == 0

    def test_coastal_places_have_sea_state(self, provider):
        assert provider.fetch("Reykjavik").marine is not None

    def test_inland_places_have_none(self, provider):
        assert provider.fetch("Madrid").marine is None

    def test_coordinates_are_accepted(self, provider):
        bundle = provider.fetch("48.85,2.35")
        assert bundle.place.lat == pytest.approx(48.85)

    def test_unknown_place_still_answers(self, provider):
        bundle = provider.fetch("Zzyzx Nowhere")
        assert bundle.current.temp_c is not None
        assert bundle.place.name == "Zzyzx Nowhere"

    def test_carries_a_demo_notice(self, provider):
        assert any("demo" in notice.lower() for notice in provider.fetch("London").notices)

    def test_alerts_are_consistent_with_the_forecast(self, provider):
        for city in ("Phoenix", "Tromso", "Singapore", "London", "Nuuk"):
            bundle = provider.fetch(city, 3)
            first = bundle.daily[0]
            for alert in bundle.alerts:
                if alert.event == "Heat":
                    assert first.maxtemp_c > 38
                if alert.event == "Wind":
                    assert first.maxwind_kph > 75

    def test_search_finds_places(self, provider):
        assert any(r["name"] == "London" for r in provider.search("lond"))

    def test_search_handles_empty_input(self, provider):
        assert provider.search("") == []

    def test_search_echoes_coordinates(self, provider):
        assert provider.search("10.5,20.5")[0]["country"] == "Coordinates"


class StubProvider:
    """A provider that fails on demand, for exercising the cache decorator."""

    name = "stub"

    def __init__(self, bundle):
        self.bundle = bundle
        self.calls = 0
        self.fail = False

    def fetch(self, query, days=3):
        self.calls += 1
        if self.fail:
            raise ProviderError("upstream down", 502)
        return self.bundle

    def search(self, query, limit=8):
        self.calls += 1
        return [{"name": query}]


class TestCachingProvider:
    def build(self, bundle, **kwargs):
        stub = StubProvider(bundle)
        cache = TTLCache(**{"ttl": 300.0, "stale_ttl": 3600.0, **kwargs})
        return stub, CachingProvider(stub, cache, TTLCache(ttl=60))

    def test_returns_the_same_type_as_the_inner_provider(self, provider):
        bundle = provider.fetch("London")
        _, cached = self.build(bundle)
        assert isinstance(cached.fetch("London"), ProviderBundle)

    def test_second_call_is_served_from_cache(self, provider):
        stub, cached = self.build(provider.fetch("London"))
        first = cached.fetch("London")
        second = cached.fetch("London")
        assert stub.calls == 1
        assert first.cached is False and second.cached is True

    def test_different_queries_are_cached_separately(self, provider):
        stub, cached = self.build(provider.fetch("London"))
        cached.fetch("London")
        cached.fetch("Paris")
        assert stub.calls == 2

    def test_stale_data_is_served_when_upstream_fails(self, provider):
        stub, cached = self.build(provider.fetch("London"), ttl=0.01)
        cached.fetch("London")
        import time
        time.sleep(0.05)
        stub.fail = True
        result = cached.fetch("London")
        assert result.stale is True
        assert any("Live update failed" in n for n in result.notices)

    def test_error_propagates_when_there_is_nothing_cached(self, provider):
        stub, cached = self.build(provider.fetch("London"))
        stub.fail = True
        with pytest.raises(ProviderError):
            cached.fetch("Nowhere")

    def test_invalidate_forces_a_refetch(self, provider):
        stub, cached = self.build(provider.fetch("London"))
        cached.fetch("London")
        cached.invalidate("London")
        cached.fetch("London")
        assert stub.calls == 2

    def test_search_is_cached(self, provider):
        stub, cached = self.build(provider.fetch("London"))
        cached.search("abc")
        cached.search("abc")
        assert stub.calls == 1


class FakeHttp:
    def __init__(self, payloads):
        self.payloads = payloads
        self.requests = []

    def get_json(self, url, params=None):
        self.requests.append((url, params))
        for fragment, payload in self.payloads.items():
            if fragment in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise ProviderError("unexpected url", 500)


FORECAST = {
    "location": {
        "name": "London", "region": "City of London", "country": "United Kingdom",
        "lat": 51.52, "lon": -0.11, "tz_id": "Europe/London",
        "localtime_epoch": 1787236200, "localtime": "2026-08-20 15:30",
    },
    "current": {
        "last_updated_epoch": 1787235000, "temp_c": 19.0, "is_day": 1,
        "condition": {"text": "Partly cloudy", "code": 1003}, "wind_kph": 14.4,
        "wind_degree": 210, "wind_dir": "SSW", "pressure_mb": 1015.0, "precip_mm": 0.0,
        "humidity": 64, "cloud": 50, "gust_kph": 21.6, "uv": 4.0, "vis_km": 10.0,
        "air_quality": {"pm2_5": 8.1, "pm10": 12.4, "o3": 60.0, "no2": 14.0,
                        "so2": 2.0, "co": 220.0, "us-epa-index": 1, "gb-defra-index": 2},
    },
    "forecast": {"forecastday": [{
        "date": "2026-08-20", "date_epoch": 1787184000,
        "day": {"maxtemp_c": 22.0, "mintemp_c": 14.0, "avgtemp_c": 18.0,
                "maxwind_kph": 20.0, "totalprecip_mm": 1.2, "totalsnow_cm": 0.0,
                "avghumidity": 68, "daily_chance_of_rain": 40, "daily_chance_of_snow": 0,
                "uv": 5.0, "condition": {"text": "Light rain", "code": 1183}},
        "astro": {"sunrise": "05:55 AM", "sunset": "08:12 PM", "moonrise": "No moonrise",
                  "moonset": "11:40 PM", "moon_phase": "First Quarter", "moon_illumination": "48"},
        "hour": [{
            "time_epoch": 1787184000 + i * 3600, "time": "2026-08-20 00:00",
            "temp_c": 15.0 + i * 0.2, "humidity": 70, "wind_kph": 12.0, "wind_degree": 200,
            "pressure_mb": 1014.0, "precip_mm": 0.1 if i in (4, 5) else 0.0,
            "chance_of_rain": 60 if i in (4, 5) else 5, "chance_of_snow": 0,
            "cloud": 40, "uv": 3.0, "vis_km": 10.0, "gust_kph": 18.0,
            "is_day": 1 if 6 <= i <= 19 else 0,
            "condition": {"text": "Cloudy", "code": 1006},
        } for i in range(24)],
    }]},
    "alerts": {"alert": [{
        "headline": "Yellow warning of rain", "event": "Rain", "severity": "Moderate",
        "areas": "London", "effective": "2026-08-20 12:00", "expires": "2026-08-20 22:00",
        "desc": "Spray and flooding possible.", "instruction": "Allow extra journey time.",
    }]},
}

MARINE = {"forecast": {"forecastday": [{"hour": [
    {"time_epoch": 1787184000 + i * 3600, "sig_ht_mt": 1.2, "swell_period_secs": 6.0,
     "swell_dir": 220, "water_temp_c": 17.0} for i in range(24)
]}]}}


class TestWeatherAPIProvider:
    def build(self, payloads=None):
        http = FakeHttp(payloads or {"forecast.json": FORECAST, "marine.json": MARINE})
        return http, WeatherAPIProvider(http, api_key="k", base_url="https://x/v1/")

    def test_requires_a_key(self):
        with pytest.raises(ValueError):
            WeatherAPIProvider(FakeHttp({}), api_key="", base_url="https://x/v1/")

    def test_satisfies_the_protocol(self):
        _, p = self.build()
        assert isinstance(p, WeatherProvider)

    def test_translates_into_the_domain_shape(self):
        _, p = self.build()
        bundle = p.fetch("London", 1)
        assert isinstance(bundle, ProviderBundle)
        assert bundle.place.name == "London"
        assert bundle.place.utc_offset_hours == 1.0
        assert bundle.current.temp_c == 19.0
        assert bundle.current.condition.slug == "partly-cloudy"
        assert bundle.current.wind_dir_16 == "SSW"
        assert len(bundle.hourly) == 24
        assert len(bundle.daily) == 1

    def test_computes_its_own_feels_like(self):
        _, p = self.build()
        current = p.fetch("London", 1).current
        assert current.feels_basis == "apparent temperature"

    def test_maps_air_quality(self):
        _, p = self.build()
        air = p.fetch("London", 1).air
        assert air.epa_index == 1
        assert air.defra_label == "Low"
        assert air.dominant == "pm2_5"

    def test_parses_astronomy_clock_times(self):
        _, p = self.build()
        day = p.fetch("London", 1).daily[0]
        assert day.sunrise_epoch and day.sunset_epoch
        assert day.sunset_epoch > day.sunrise_epoch
        assert day.daylight_minutes == pytest.approx(14 * 60 + 17, abs=2)
        assert day.moonrise_epoch is None, "'No moonrise' must not become a timestamp"
        assert day.moon_illumination == 48.0

    def test_maps_alerts_with_a_tone(self):
        _, p = self.build()
        alert = p.fetch("London", 1).alerts[0]
        assert alert.event == "Rain"
        assert alert.tone == "warn"
        assert alert.expires_epoch > alert.effective_epoch

    def test_marine_absence_is_not_an_error(self):
        http = FakeHttp({"forecast.json": FORECAST, "marine.json": ProviderError("inland", 400)})
        p = WeatherAPIProvider(http, api_key="k", base_url="https://x/v1/")
        assert p.fetch("Madrid", 1).marine is None

    def test_missing_observation_is_an_error(self):
        http = FakeHttp({"forecast.json": {"location": {}, "current": {}}})
        p = WeatherAPIProvider(http, api_key="k", base_url="https://x/v1/")
        with pytest.raises(ProviderError):
            p.fetch("Nowhere", 1)

    def test_search_translates_rows(self):
        http = FakeHttp({"search.json": [
            {"name": "Paris", "region": "Ile-de-France", "country": "France", "lat": 48.87, "lon": 2.33},
        ]})
        p = WeatherAPIProvider(http, api_key="k", base_url="https://x/v1/")
        rows = p.search("paris")
        assert rows[0]["label"] == "Paris, Ile-de-France, France"

    def test_search_short_circuits_on_empty(self):
        http, p = self.build()
        assert p.search("  ") == []
        assert http.requests == []
