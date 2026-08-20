"""Scorers are policy, so the tests pin the behaviour, not the arithmetic."""

import pytest

from weatherapp.advice.comfort import comfort
from weatherapp.advice.guidance import outfit, sunscreen, umbrella
from weatherapp.advice.registry import all_scorers, band_for, score_all
from weatherapp.advice.snapshot import Snapshot


def snapshot(**overrides):
    hours = overrides.pop("hourly", None)
    if hours is None:
        hours = [
            {"t": i * 3600, "temp_c": 18.0, "precip_mm": 0.0, "chance_rain": 5,
             "uv": 3.0, "dewpoint_c": 9.0, "wind_kph": 10.0}
            for i in range(30)
        ]
    base = dict(
        temp_c=20.0, humidity=55.0, wind_kph=12.0, precip_mm=0.0, cloud=40.0,
        uv=3.0, feels_c=19.0, now_epoch=0, hourly=hours, gust_kph=18.0,
        vis_km=20.0, aqi_epa=1, moon_illumination=20.0, water_temp_c=None,
        daylight_hours=13.0, next_24h_precip_mm=0.0, uv_max_today=4.0,
        chance_rain=5, golden_evening_epoch=None, frost={"risk": False},
    )
    base.update(overrides)
    return Snapshot(**base)


class TestRegistry:
    def test_every_scorer_is_registered(self):
        keys = {s.key for s in all_scorers()}
        assert keys == {"running", "cycling", "laundry", "stargazing", "beach",
                        "gardening", "photography", "kite"}

    def test_scorers_return_a_uniform_shape(self):
        for result in score_all(snapshot()):
            assert set(result) >= {"key", "label", "icon", "score", "band", "tone", "reason", "reasons"}
            assert 0 <= result["score"] <= 100
            assert result["reason"]

    def test_scores_are_always_clamped(self):
        brutal = snapshot(temp_c=48, humidity=95, wind_kph=140, precip_mm=40, uv=13, aqi_epa=6, feels_c=60)
        for result in score_all(brutal):
            assert 0 <= result["score"] <= 100

    @pytest.mark.parametrize("score,label", [(95, "Excellent"), (70, "Good"), (50, "Fair"), (30, "Poor"), (5, "Forget it")])
    def test_bands(self, score, label):
        assert band_for(score)[0] == label


class TestScorerBehaviour:
    def get(self, results, key):
        return next(r for r in results if r["key"] == key)

    def test_running_prefers_cool_over_warm(self):
        cool = self.get(score_all(snapshot(temp_c=10, feels_c=9)), "running")["score"]
        warm = self.get(score_all(snapshot(temp_c=30, feels_c=32)), "running")["score"]
        assert cool > warm

    def test_kite_inverts_the_wind_preference(self):
        results_calm = score_all(snapshot(wind_kph=3, gust_kph=4))
        results_breezy = score_all(snapshot(wind_kph=28, gust_kph=33))
        assert self.get(results_calm, "kite")["score"] < self.get(results_breezy, "kite")["score"]
        assert self.get(results_calm, "cycling")["score"] > self.get(results_breezy, "cycling")["score"]

    def test_laundry_needs_dry_moving_air(self):
        good = self.get(score_all(snapshot(temp_c=22, humidity=35, wind_kph=20)), "laundry")["score"]
        bad = self.get(score_all(snapshot(temp_c=3, humidity=95, wind_kph=1)), "laundry")["score"]
        assert good > bad

    def test_laundry_is_hopeless_in_rain(self):
        assert self.get(score_all(snapshot(precip_mm=2.0)), "laundry")["score"] <= 12

    def test_stargazing_punishes_cloud_and_moon(self):
        clear = self.get(score_all(snapshot(cloud=2, moon_illumination=0)), "stargazing")["score"]
        washed = self.get(score_all(snapshot(cloud=95, moon_illumination=100)), "stargazing")["score"]
        assert clear > 90 and washed < 20

    def test_photography_prefers_broken_cloud(self):
        broken = self.get(score_all(snapshot(cloud=45)), "photography")["score"]
        flat = self.get(score_all(snapshot(cloud=100)), "photography")["score"]
        assert broken > flat

    def test_gardening_carries_watering_advice(self):
        wet = self.get(score_all(snapshot(next_24h_precip_mm=8)), "gardening")
        assert "Skip watering" in wet["watering"]
        dry = self.get(score_all(snapshot(temp_c=28, next_24h_precip_mm=0)), "gardening")
        assert "Water deeply" in dry["watering"]

    def test_scorer_explains_itself(self):
        hot = self.get(score_all(snapshot(temp_c=32, feels_c=34)), "running")
        assert "warm" in hot["reason"].lower()


class TestComfort:
    def test_ideal_conditions_score_high(self):
        assert comfort(snapshot(feels_c=21, humidity=50, wind_kph=6, uv=2))["score"] >= 95

    def test_extremes_score_low(self):
        result = comfort(snapshot(feels_c=45, humidity=95, wind_kph=60, precip_mm=6, uv=12, aqi_epa=6))
        assert result["score"] == 0
        assert result["band"] == "Hostile"

    def test_detractors_are_ranked_and_named(self):
        result = comfort(snapshot(feels_c=38, humidity=90, wind_kph=45))
        causes = [d["cause"] for d in result["detractors"]]
        assert causes[0] == "temperature"
        assert result["detractors"][0]["cost"] >= result["detractors"][-1]["cost"]

    def test_cold_and_hot_both_penalised(self):
        assert comfort(snapshot(feels_c=-15))["score"] < 40
        assert comfort(snapshot(feels_c=40))["score"] < 40

    def test_temperature_alone_can_sink_the_score(self):
        # A single dominant factor must be able to reach the bottom bands.
        assert comfort(snapshot(feels_c=-25, humidity=50, wind_kph=5, uv=0))["band"] in {"Punishing", "Hostile"}


class TestGuidance:
    def wet_hours(self, start, length, mm=1.0):
        return [
            {"t": i * 3600, "temp_c": 15.0, "dewpoint_c": 9.0,
             "precip_mm": mm if start <= i < start + length else 0.0,
             "chance_rain": 90 if start <= i < start + length else 5,
             "uv": 2.0, "wind_kph": 10.0}
            for i in range(30)
        ]

    def test_umbrella_not_needed_when_dry(self):
        result = umbrella(snapshot())
        assert result["needed"] is False
        assert result["tone"] == "ok"

    def test_umbrella_needed_and_timed(self):
        result = umbrella(snapshot(hourly=self.wet_hours(3, 3)))
        assert result["needed"] is True
        assert "3h" in result["detail"] or "min" in result["detail"]

    def test_umbrella_reports_rain_already_falling(self):
        result = umbrella(snapshot(hourly=self.wet_hours(0, 3)))
        assert "Raining now" in result["detail"]

    def test_umbrella_ignores_rain_beyond_twelve_hours(self):
        assert umbrella(snapshot(hourly=self.wet_hours(20, 3)))["needed"] is False

    def test_sunscreen_thresholds(self):
        assert sunscreen(snapshot(uv_max_today=1))["needed"] is False
        strong = sunscreen(snapshot(uv_max_today=10))
        assert strong["needed"] is True and strong["tone"] == "bad"
        assert strong["burn_minutes"] > 0

    @pytest.mark.parametrize("feels,expected", [
        (-15, "Serious cold"), (-3, "Freezing"), (5, "Cold"), (12, "Cool"),
        (18, "Mild"), (24, "Warm"), (30, "Hot"), (40, "Dangerous heat"),
    ])
    def test_outfit_bands(self, feels, expected):
        assert expected in outfit(snapshot(feels_c=feels))["headline"]

    def test_outfit_adds_rain_gear(self):
        extras = outfit(snapshot(feels_c=15, chance_rain=80))["extras"]
        assert any("Waterproof" in e for e in extras)

    def test_outfit_does_not_suggest_a_packable_jacket_in_a_parka(self):
        extras = outfit(snapshot(feels_c=-10, chance_rain=30))["extras"]
        assert not any("Packable" in e for e in extras)

    def test_outfit_warns_umbrella_will_invert(self):
        extras = outfit(snapshot(feels_c=10, wind_kph=50))["extras"]
        assert any("invert" in e for e in extras)


class TestBuild:
    def test_advice_block_is_complete(self, report):
        a = report.advice
        assert a.summary.endswith(".")
        assert a.summary[0].isupper()
        assert len(a.activities) == 8
        assert a.best_activity in a.activities
        assert a.comfort["score"] >= 0
        assert isinstance(a.rain_windows, list)
        assert a.uv_max_today >= 0

    def test_best_activity_is_actually_the_best(self, report):
        assert report.advice.best_activity["score"] == max(a["score"] for a in report.advice.activities)

    def test_summary_mentions_the_place(self, report):
        assert report.place.name in report.advice.summary
