"""The diagnose endpoint reports secrets-adjacent data, so its gate is the test."""

import pytest

from weatherapp import create_app
from weatherapp.config import Settings


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("API_KEY", "0123456789abcdef0123456789abcdef")
    return create_app(settings=Settings())


class TestGate:
    def test_absent_without_a_configured_token(self, app, monkeypatch):
        monkeypatch.delenv("DIAGNOSTIC_TOKEN", raising=False)
        assert app.test_client().get("/api/v1/diagnose").status_code == 404

    def test_wrong_token_is_404_not_403(self, app, monkeypatch):
        """403 would confirm the endpoint exists on a public deployment."""
        monkeypatch.setenv("DIAGNOSTIC_TOKEN", "correct-horse")
        assert app.test_client().get("/api/v1/diagnose?token=wrong").status_code == 404

    def test_empty_token_never_authorises(self, app, monkeypatch):
        monkeypatch.setenv("DIAGNOSTIC_TOKEN", "")
        assert app.test_client().get("/api/v1/diagnose?token=").status_code == 404


class TestPayload:
    def test_never_returns_the_key(self, app, monkeypatch):
        monkeypatch.setenv("DIAGNOSTIC_TOKEN", "letmein")
        body = app.test_client().get("/api/v1/diagnose?token=letmein").get_data(as_text=True)
        assert "0123456789abcdef0123456789abcdef" not in body
        assert "0123****" in body or "****cdef" in body

    def test_reports_the_fields_needed_to_diagnose(self, app, monkeypatch):
        monkeypatch.setenv("DIAGNOSTIC_TOKEN", "letmein")
        payload = app.test_client().get("/api/v1/diagnose?token=letmein").get_json()
        assert set(payload) >= {"provider", "base_url", "key", "verdict", "probes"}
        assert set(payload["key"]) >= {"source", "status", "masked", "length", "charset", "normalised"}


class TestDiagnoseLogic:
    def _settings(self):
        return Settings(base_url="https://api.weatherapi.com/v1/", http_timeout=1)

    def test_no_probes_run_without_a_usable_key(self):
        from weatherapp.diagnostics import diagnose
        report = diagnose(self._settings(), "your_api_key_here", "API_KEY")
        assert report["probes"] == []
        assert report["verdict"]["state"] == "placeholder"

    def test_matrix_covers_every_changed_dimension(self):
        from weatherapp.diagnostics import probe

        class Recorder:
            def __init__(self): self.seen = []
            def get_json(self, url, params=None):
                self.seen.append((url, params))
                return {"error": {"code": 2006, "message": "API key is invalid."}}

        http = Recorder()
        results = probe(self._settings(), "abc", "  abc-raw  ", http=http)
        assert {r["scheme"] for r in results} == {"https", "http"}
        assert {r["style"] for r in results} == {"params", "inline"}
        assert {r["value"] for r in results} == {"normalised", "raw"}
        assert len(results) == 8

    def test_identical_raw_and_normalised_is_not_probed_twice(self):
        from weatherapp.diagnostics import probe

        class Stub:
            def get_json(self, url, params=None):
                return {"error": {"code": 2006}}

        results = probe(self._settings(), "abc", "abc", http=Stub())
        assert len(results) == 4

    def test_unreachable_is_not_reported_as_a_bad_key(self):
        from weatherapp.diagnostics import verdict
        state = verdict([{"outcome": "unreachable", "detail": "timeout"}])
        assert state["state"] == "unreachable"
        assert "not" in state["detail"].lower()

    def test_raw_only_success_blames_normalisation(self):
        from weatherapp.diagnostics import verdict
        state = verdict([{"outcome": "ok", "scheme": "https", "style": "params", "value": "raw"}])
        assert any("normalisation is corrupting" in n for n in state["notes"])
