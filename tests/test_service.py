"""Assembly order and the injected-clock contract."""

from datetime import datetime, timedelta, timezone


from weatherapp.config import Settings
from weatherapp.domain import Report
from weatherapp.infrastructure.clock import FrozenClock
from weatherapp.providers.demo import DemoProvider
from weatherapp.services import ReportService


class TestAssembly:
    def test_builds_a_full_report(self, report):
        assert isinstance(report, Report)
        assert report.advice is not None, "advice must be built after solar geometry"
        assert report.astro is not None

    def test_enriches_the_observation_for_the_ui(self, report):
        assert report.current.barb is not None, "the station plot needs barb data"
        assert report.current.uv_band is not None

    def test_pressure_trend_is_attached(self, report):
        assert report.advice.pressure_trend["direction"] in {"rising", "falling", "steady", "unknown"}

    def test_meta_records_provenance(self, report):
        assert report.meta.provider == "demo"
        assert report.meta.version == "test"
        assert report.meta.forecast_days == 3

    def test_serialises_to_plain_json_types(self, report):
        import json
        payload = report.to_dict()
        assert json.loads(json.dumps(payload))["place"]["name"] == "London"

    def test_floats_are_rounded_at_the_boundary(self, report):
        for hour in report.to_dict()["hourly"]:
            assert len(str(hour["temp_c"]).split(".")[-1]) <= 4


class TestClockInjection:
    def test_now_is_quantised_for_stable_etags(self, provider, settings):
        base = datetime(2026, 8, 20, 14, 30, 20, tzinfo=timezone.utc)
        a = ReportService(provider, FrozenClock(base), settings).report("London")
        b = ReportService(provider, FrozenClock(base + timedelta(seconds=15)), settings).report("London")
        assert a.meta.now_epoch == b.meta.now_epoch

    def test_now_advances_past_the_quantum(self, provider, settings):
        base = datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc)
        a = ReportService(provider, FrozenClock(base), settings).report("London")
        b = ReportService(provider, FrozenClock(base + timedelta(minutes=5)), settings).report("London")
        assert b.meta.now_epoch > a.meta.now_epoch

    def test_report_is_reproducible_for_a_frozen_clock(self, settings):
        clock = FrozenClock(datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc))
        first = ReportService(DemoProvider(clock), clock, settings).report("Oslo").to_dict()
        second = ReportService(DemoProvider(clock), clock, settings).report("Oslo").to_dict()
        assert first == second


class TestSolarIntegration:
    def test_daylight_is_plausible(self, report):
        assert 0 <= report.astro.daylight_minutes <= 1440

    def test_sun_path_covers_the_day(self, report):
        assert len(report.astro.sun_path) == 49

    def test_solar_elevation_matches_day_or_night(self, report):
        if report.current.is_day:
            assert report.astro.solar_elevation > -6
        else:
            assert report.astro.solar_elevation < 6

    def test_southern_hemisphere_gains_daylight_in_august(self, settings):
        clock = FrozenClock(datetime(2026, 8, 20, 12, tzinfo=timezone.utc))
        service = ReportService(DemoProvider(clock), clock, settings)
        assert service.report("Sydney").astro.daylight_delta_minutes > 0
        assert service.report("London").astro.daylight_delta_minutes < 0


class TestCompare:
    def test_returns_one_report_each(self, service):
        reports = service.compare(["London", "Cairo", "Oslo"])
        assert [r.place.name for r in reports] == ["London", "Cairo", "Oslo"]

    def test_skips_blank_queries(self, service):
        assert len(service.compare(["London", "  ", ""])) == 1


class TestSettings:
    def test_demo_when_no_key(self):
        assert Settings(api_key="").live is False
        assert Settings(api_key="").active_provider == "demo"

    def test_live_when_key_present(self):
        assert Settings(api_key="abc").live is True

    def test_provider_can_be_forced(self):
        assert Settings(api_key="abc", provider="demo").live is False
        assert Settings(api_key="", provider="weatherapi").live is True

    def test_from_env_reads_overrides(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "zzz")
        monkeypatch.setenv("CACHE_TTL", "42")
        monkeypatch.setenv("DEFAULT_PLACE", "Oslo")
        settings = Settings.from_env()
        assert settings.api_key == "zzz"
        assert settings.cache_ttl == 42.0
        assert settings.default_place == "Oslo"

    def test_from_env_ignores_a_bad_provider(self, monkeypatch):
        monkeypatch.setenv("WEATHER_PROVIDER", "nonsense")
        assert Settings.from_env().provider == "auto"


class TestPlaces:
    def test_gazetteer_rows_are_sane(self):
        from weatherapp import places
        for place in places.PLACES:
            assert -90 <= place.lat <= 90
            assert -180 <= place.lon <= 180
            assert 0 <= place.base_rh <= 100
            assert 0 <= place.wetness <= 1
            assert place.season_amp_c >= 0
            assert place.tz_id

    def test_names_are_unique(self):
        from weatherapp import places
        names = [p.key for p in places.PLACES]
        assert len(names) == len(set(names))

    def test_lookup_forms(self):
        from weatherapp import places
        assert places.lookup("London").name == "London"
        assert places.lookup("london").name == "London"
        assert places.lookup("Tokyo, Japan").name == "Tokyo"
        assert places.lookup("") is None

    def test_search_ranks_prefixes_first(self):
        from weatherapp import places
        assert places.search("lon")[0]["name"] == "London"
