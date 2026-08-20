"""Formulas are checked against the values the issuing services publish."""

from datetime import datetime, timezone

import pytest

from weatherapp.meteorology import air, conditions, solar, thermal, timeline, units, wind


class TestThermal:
    def test_dew_point_matches_reference(self):
        assert thermal.dew_point_c(20, 50) == pytest.approx(9.3, abs=0.1)
        assert thermal.dew_point_c(30, 80) == pytest.approx(26.2, abs=0.2)

    def test_relative_humidity_inverts_dew_point(self):
        for temp, rh in ((20, 50), (5, 90), (33, 22)):
            dew = thermal.dew_point_c(temp, rh)
            assert thermal.relative_humidity(temp, dew) == pytest.approx(rh, abs=0.5)

    def test_heat_index_matches_nws_table(self):
        # NWS table: 90F/70% -> about 106F; 32C/70% is 89.6F.
        assert thermal.heat_index_c(32, 70) == pytest.approx(40.4, abs=0.7)

    def test_heat_index_falls_back_below_threshold(self):
        # Below 80F the regression is not used; result stays near air temperature.
        assert thermal.heat_index_c(20, 40) == pytest.approx(20, abs=2.0)

    def test_wind_chill_matches_nws_formula(self):
        assert thermal.wind_chill_c(-5, 30) == pytest.approx(-12.9, abs=0.2)

    def test_wind_chill_undefined_above_ten_degrees(self):
        assert thermal.wind_chill_c(15, 40) == 15

    def test_wind_chill_undefined_in_light_air(self):
        assert thermal.wind_chill_c(0, 3) == 0

    def test_humidex_matches_reference(self):
        assert thermal.humidex(30, 70) == pytest.approx(41.2, abs=0.5)

    @pytest.mark.parametrize("temp,wind,expected", [
        (-3, 25, "wind chill"),
        (18, 10, "apparent temperature"),
        (34, 5, "heat index"),
    ])
    def test_feels_like_picks_the_right_index(self, temp, wind, expected):
        assert thermal.feels_like(temp, 60, wind)["basis"] == expected

    def test_uv_bands(self):
        assert thermal.uv_band(1)["label"] == "Low"
        assert thermal.uv_band(6)["label"] == "High"
        assert thermal.uv_band(12)["label"] == "Extreme"
        assert thermal.uv_band(None)["label"] == "Unknown"


class TestWind:
    @pytest.mark.parametrize("deg,expected", [(0, "N"), (90, "E"), (200, "SSW"), (350, "N"), (359.9, "N")])
    def test_cardinals(self, deg, expected):
        assert wind.cardinal(deg) == expected

    def test_cardinal_handles_missing(self):
        assert wind.cardinal(None) == "--"

    @pytest.mark.parametrize("kph,force", [(0, 0), (10, 2), (45, 6), (130, 12)])
    def test_beaufort_scale(self, kph, force):
        assert wind.beaufort(kph)["force"] == force

    def test_barb_decomposes_to_station_model(self):
        # 120 km/h is 65 knots: one pennant (50), one full barb (10), one half (5).
        assert wind.barb(120) == {"knots": 65, "pennants": 1, "full": 1, "half": 1, "calm": False}

    def test_barb_marks_calm_below_three_knots(self):
        assert wind.barb(2)["calm"] is True

    def test_barb_totals_match_knots(self):
        for kph in range(0, 200, 7):
            b = wind.barb(kph)
            assert b["pennants"] * 50 + b["full"] * 10 + b["half"] * 5 == b["knots"]


class TestAir:
    @pytest.mark.parametrize("value,expected", [(0, 0), (12.0, 50), (35.5, 101), (55.5, 151), (250.5, 301)])
    def test_pm25_breakpoints_match_epa(self, value, expected):
        assert air.sub_index("pm2_5", value) == expected

    @pytest.mark.parametrize("value,expected", [(54, 50), (154, 100), (254, 150)])
    def test_pm10_breakpoints_match_epa(self, value, expected):
        assert air.sub_index("pm10", value) == expected

    def test_gases_have_no_ugm3_breakpoints(self):
        assert air.sub_index("o3", 100) is None

    def test_categories(self):
        assert air.category(30)["label"] == "Good"
        assert air.category(120)["tone"] == "warn"
        assert air.category(250)["tone"] == "bad"

    def test_defra_bands(self):
        assert air.defra_label(2) == "Low"
        assert air.defra_label(7) == "High"
        assert air.defra_label(10) == "Very high"


class TestSolar:
    LONDON = (51.5074, -0.1278)

    def test_summer_solstice_noon_elevation(self):
        pos = solar.sun_position(datetime(2026, 6, 21, 12, tzinfo=timezone.utc), *self.LONDON)
        # 90 - latitude + declination
        assert pos.elevation == pytest.approx(90 - 51.5074 + 23.44, abs=0.6)

    def test_solar_noon_is_due_south_in_northern_hemisphere(self):
        pos = solar.sun_position(datetime(2026, 6, 21, 12, 1, tzinfo=timezone.utc), *self.LONDON)
        assert pos.azimuth == pytest.approx(180, abs=2)

    def test_solstice_daylight_length(self):
        events = solar.solar_events(datetime(2026, 6, 21, 12, tzinfo=timezone.utc), *self.LONDON)
        assert events["daylight_minutes"] == pytest.approx(16 * 60 + 38, abs=5)

    def test_sunrise_before_sunset(self):
        events = solar.solar_events(datetime(2026, 3, 15, 12, tzinfo=timezone.utc), *self.LONDON)
        assert events["sunrise"] < events["solar_noon"] < events["sunset"]
        assert events["dawn"] < events["sunrise"]
        assert events["dusk"] > events["sunset"]

    def test_polar_day_and_night(self):
        tromso = (69.65, 18.95)
        assert solar.solar_events(datetime(2026, 6, 21, 12, tzinfo=timezone.utc), *tromso)["daylight_minutes"] == 1440
        assert solar.solar_events(datetime(2026, 12, 21, 12, tzinfo=timezone.utc), *tromso)["daylight_minutes"] == 0

    def test_daylight_delta_is_negative_after_solstice(self):
        delta = solar.daylight_delta(datetime(2026, 8, 20, 12, tzinfo=timezone.utc), *self.LONDON)
        assert delta < 0

    def test_daylight_delta_is_positive_in_spring(self):
        delta = solar.daylight_delta(datetime(2026, 3, 20, 12, tzinfo=timezone.utc), *self.LONDON)
        assert delta > 0

    def test_moon_phase_cycles(self):
        phase = solar.moon_phase(datetime(2026, 8, 20, 12, tzinfo=timezone.utc))
        assert 0 <= phase["illumination"] <= 100
        assert 0 <= phase["age_days"] < 29.6
        assert phase["name"] in solar.MOON_PHASE_NAMES

    def test_sun_path_spans_a_day(self):
        path = solar.sun_path(datetime(2026, 8, 20, 12, tzinfo=timezone.utc), *self.LONDON, samples=25)
        assert len(path) == 25
        assert path[-1]["t"] - path[0]["t"] == pytest.approx(86400, abs=60)


class TestTimeline:
    @staticmethod
    def hours(**overrides):
        base = []
        for i in range(30):
            base.append({
                "t": i * 3600, "temp_c": 15.0, "dewpoint_c": 8.0, "pressure_mb": 1010.0,
                "precip_mm": 0.0, "chance_rain": 0, "wind_kph": 10.0,
                **{k: v(i) for k, v in overrides.items()},
            })
        return base

    def test_pressure_trend_detects_a_fall(self):
        hours = self.hours(pressure_mb=lambda i: 1020 - i * 1.5)
        trend = timeline.pressure_trend(hours, 6 * 3600, 1011.0)
        assert trend["direction"] == "falling"
        assert trend["delta_3h"] < 0

    def test_pressure_trend_steady(self):
        trend = timeline.pressure_trend(self.hours(), 6 * 3600, 1010.0)
        assert trend["direction"] == "steady"

    def test_pressure_trend_without_reading(self):
        assert timeline.pressure_trend(self.hours(), 0, None)["direction"] == "unknown"

    def test_rain_windows_group_contiguous_hours(self):
        hours = self.hours(precip_mm=lambda i: 0.5 if 3 <= i <= 5 else 0.0)
        windows = timeline.rain_windows(hours, 0)
        assert len(windows) == 1
        assert windows[0]["hours"] == 3
        assert windows[0]["total_mm"] == pytest.approx(1.5)

    def test_rain_windows_separate_distinct_events(self):
        hours = self.hours(precip_mm=lambda i: 0.5 if i in (2, 3, 10, 11) else 0.0)
        assert len(timeline.rain_windows(hours, 0)) == 2

    def test_dry_windows_ignore_short_gaps(self):
        hours = self.hours(precip_mm=lambda i: 0.0 if i == 0 else 1.0)
        assert timeline.dry_windows(hours, 0, min_hours=2) == []

    def test_frost_risk_levels(self):
        assert timeline.frost_risk([{"temp_c": -5, "dewpoint_c": -8, "t": 0}])["level"] == "hard"
        assert timeline.frost_risk([{"temp_c": -0.5, "dewpoint_c": -2, "t": 0}])["level"] == "frost"
        assert timeline.frost_risk([{"temp_c": 2, "dewpoint_c": 0, "t": 0}])["level"] == "ground"
        assert timeline.frost_risk([{"temp_c": 12, "dewpoint_c": 8, "t": 0}])["risk"] is False

    def test_air_out_window_prefers_indoor_match(self):
        hours = self.hours(temp_c=lambda i: 21.0 if i == 5 else 3.0)
        assert timeline.air_out_window(hours, 0, indoor_c=21)["t"] == 5 * 3600

    def test_air_out_window_skips_wet_hours(self):
        hours = self.hours(temp_c=lambda i: 21.0, precip_mm=lambda i: 1.0)
        assert timeline.air_out_window(hours, 0) is None

    def test_extremes_and_totals(self):
        hours = self.hours(temp_c=lambda i: float(i), precip_mm=lambda i: 0.5)
        extremes = timeline.extremes(hours, 0, horizon_h=10)
        assert extremes["warmest"]["temp_c"] == 10
        assert extremes["coldest"]["temp_c"] == 0
        assert extremes["swing_c"] == 10
        assert timeline.total_precip(hours, 0, horizon_h=10) == pytest.approx(5.5)

    def test_peak_uv(self):
        hours = self.hours(uv=lambda i: float(i))
        value, at = timeline.peak_uv(hours, 0, horizon_h=5)
        assert (value, at) == (5.0, 5 * 3600)


class TestConditions:
    def test_known_codes_map(self):
        assert conditions.slug_for_code(1000) == "clear"
        assert conditions.slug_for_code(1195) == "rain-heavy"
        assert conditions.slug_for_code(1282) == "thunder-rain"

    def test_unknown_code_falls_back_to_text(self):
        assert conditions.slug_for_code(99999, "Heavy rain shower") == "rain"
        assert conditions.slug_for_code(None, "Freezing fog patches") == "fog"

    def test_unknown_everything_is_still_valid(self):
        assert conditions.slug_for_code(None, "") in conditions.CONDITIONS

    def test_model_picks_snow_below_freezing(self):
        assert conditions.from_model(90, 1.0, -3)["slug"].startswith("snow")

    def test_model_picks_clear_when_dry_and_cloudless(self):
        assert conditions.from_model(2, 0, 20)["slug"] == "clear"

    def test_every_slug_is_described(self):
        for slug in conditions.CONDITIONS:
            assert conditions.label_for(slug)
            assert conditions.family_for(slug)


def test_unit_conversions():
    assert units.c_to_f(100) == 212
    assert units.f_to_c(32) == 0
    assert units.kph_to_mph(100) == pytest.approx(62.14, abs=0.01)
    assert units.kph_to_knots(100) == pytest.approx(53.996, abs=0.01)
    assert units.mb_to_inhg(1013.25) == pytest.approx(29.92, abs=0.01)
    assert units.mm_to_inches(25.4) == pytest.approx(1.0)
