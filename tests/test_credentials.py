import pytest

from weatherapp.infrastructure.credentials import sanitize

KEY = "0123456789abcdef0123456789abcdef"


class TestSanitize:
    @pytest.mark.parametrize("raw", [
        KEY,
        f"  {KEY}  ",
        f"{KEY}\r\n",
        f'"{KEY}"',
        f"'{KEY}'",
        f"“{KEY}”",
        f"API_KEY={KEY}",
        f"WEATHERAPI_KEY = {KEY}",
        f"key={KEY}",
        f'API_KEY="{KEY}"',
        f"https://api.weatherapi.com/v1/current.json?key={KEY}&q=London",
        f"http://api.weatherapi.com/v1/forecast.json?q=London&days=3&key={KEY}",
    ])
    def test_recovers_the_key_from_common_paste_mistakes(self, raw):
        result = sanitize(raw)
        assert result.value == KEY
        assert result.usable

    @pytest.mark.parametrize("raw", [None, "", "   ", '""'])
    def test_absent_values_are_missing(self, raw):
        assert sanitize(raw).status == "missing"
        assert not sanitize(raw).usable

    @pytest.mark.parametrize("raw", ["your_api_key_here", "YOUR-API-KEY-HERE", "changeme", "todo"])
    def test_placeholders_are_rejected_rather_than_sent_upstream(self, raw):
        result = sanitize(raw)
        assert result.status == "placeholder"
        assert not result.usable

    def test_wrong_shape_is_still_tried(self):
        result = sanitize("short123")
        assert result.status == "suspicious"
        assert result.usable, "a key of unexpected shape must still be attempted"

    def test_masking_never_leaks_the_middle(self):
        masked = sanitize(KEY).masked()
        assert KEY not in masked
        assert masked.startswith("0123") and masked.endswith("cdef")

    def test_repairs_are_reported_for_diagnostics(self):
        assert "stripped a key= prefix" in sanitize(f"API_KEY={KEY}").repaired
