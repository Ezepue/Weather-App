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


class TestPlaceholderDetection:
    """An enumerated list only catches the spellings someone thought of."""

    @pytest.mark.parametrize("raw", [
        "your_secret_key",          # the one that reached production
        "your_api_key_here", "YOUR-API-KEY", "your key here", "my_secret_key",
        "insert_api_key", "enter api key", "paste your key", "replace-me",
        "changeme", "CHANGEME", "todo", "TBD", "fixme", "xxx",
        "api_key", "secret_key", "access_token",
        "<your key here>", "example_key", "sample", "dummy", "placeholder",
        "none", "null", "...",
    ])
    def test_placeholders_never_reach_the_upstream(self, raw):
        result = sanitize(raw)
        assert result.status == "placeholder", f"{raw!r} would have been sent as a key"
        assert not result.usable

    @pytest.mark.parametrize("raw", [
        "0123456789abcdef0123456789abcdef",
        "9f8e7d6c5b4a392817061524334251ab",
        "abcd1234ABCD5678abcd1234ABCD5678",
        "deadbeefdeadbeefdeadbeefdeadbeef",
        "a1b2c3d4e5f60718293a4b5c6d7e8f90",
    ])
    def test_real_keys_are_not_mistaken_for_placeholders(self, raw):
        result = sanitize(raw)
        assert result.status == "ok", f"{raw!r} was wrongly rejected as a placeholder"
        assert result.value == raw

    def test_the_note_states_what_to_do(self):
        note = sanitize("your_secret_key").note
        assert "placeholder" in note.lower()
        assert "replace" in note.lower()


class TestPlaceholderReachesTheUser:
    def test_report_explains_why_data_is_synthetic(self, monkeypatch):
        from weatherapp import create_app
        from weatherapp.config import Settings

        monkeypatch.setenv("API_KEY", "your_secret_key")
        client = create_app(settings=Settings.from_env()).test_client()
        payload = client.get("/api/v1/report?q=London").get_json()

        assert payload["meta"]["provider"] == "demo", "a placeholder must not be sent upstream"
        assert any("placeholder" in n.lower() for n in payload["meta"]["notices"])

    def test_healthz_reports_the_placeholder_status(self, monkeypatch):
        from weatherapp import create_app
        from weatherapp.config import Settings

        monkeypatch.setenv("API_KEY", "your_secret_key")
        client = create_app(settings=Settings.from_env()).test_client()
        key = client.get("/api/v1/healthz").get_json()["key"]
        assert key["status"] == "placeholder"
        assert key["configured"] is False
