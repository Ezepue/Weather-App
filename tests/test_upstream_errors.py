"""The upstream error envelope is the only signal for 'why did this fail'."""

import pytest

from weatherapp.domain.protocols import ProviderError
from weatherapp.providers.weatherapi import WeatherAPIProvider


class EnvelopeHttp:
    """Returns a WeatherAPI error envelope, as the real service does on 4xx."""

    def __init__(self, code, message):
        self.payload = {"error": {"code": code, "message": message}}

    def get_json(self, url, params=None):
        return self.payload


def provider(code, message):
    return WeatherAPIProvider(
        http=EnvelopeHttp(code, message),
        api_key="0123456789abcdef0123456789abcdef",
        base_url="https://api.weatherapi.com/v1/",
        marine_enabled=False,
    )


class TestErrorTranslation:
    def test_invalid_key_is_401_with_a_remedy(self):
        with pytest.raises(ProviderError) as caught:
            provider(2006, "API key is invalid.").fetch("London")
        error = caught.value
        assert error.status == 401
        assert error.kind == "auth"
        # The bare upstream sentence is not actionable; the remedy must be.
        assert "weatherapi.com/my-account" in str(error)
        assert "doctor" in str(error)

    def test_missing_key_is_distinguished_from_invalid_key(self):
        with pytest.raises(ProviderError) as caught:
            provider(1002, "API key not provided.").fetch("London")
        assert ".env" in str(caught.value)
        assert "rejected" not in str(caught.value)

    def test_quota_exhaustion_is_429_not_401(self):
        with pytest.raises(ProviderError) as caught:
            provider(2007, "quota exceeded").fetch("London")
        assert caught.value.status == 429

    def test_disabled_key_is_401(self):
        with pytest.raises(ProviderError) as caught:
            provider(2008, "disabled").fetch("London")
        assert caught.value.status == 401

    def test_plan_restriction_is_403_and_names_marine(self):
        with pytest.raises(ProviderError) as caught:
            provider(2009, "no access").fetch("London")
        assert caught.value.status == 403
        assert "MARINE_ENABLED" in str(caught.value)

    def test_unknown_place_is_404_and_not_an_auth_failure(self):
        with pytest.raises(ProviderError) as caught:
            provider(1006, "No matching location found.").fetch("Atlantis")
        assert caught.value.status == 404
        assert caught.value.kind == "upstream"

    def test_unrecognised_code_falls_back_to_the_upstream_message(self):
        with pytest.raises(ProviderError) as caught:
            provider(4242, "Something new").fetch("London")
        assert "Something new" in str(caught.value)

    def test_search_reports_auth_failure_too(self):
        with pytest.raises(ProviderError) as caught:
            provider(2006, "API key is invalid.").search("lond")
        assert caught.value.status == 401


class TestHttpClientLayering:
    def test_client_does_not_interpret_the_envelope(self):
        """A 4xx body must reach the adapter, or the diagnosis is lost."""
        import weatherapp.infrastructure.http as http_module

        class Response:
            status_code = 401
            @staticmethod
            def json():
                return {"error": {"code": 2006, "message": "API key is invalid."}}

        decoded = http_module.HttpClient._decode(Response())
        assert decoded["error"]["code"] == 2006

    def test_server_errors_still_raise_in_the_client(self):
        import weatherapp.infrastructure.http as http_module

        class Response:
            status_code = 503
            @staticmethod
            def json():
                return {}

        with pytest.raises(ProviderError):
            http_module.HttpClient._decode(Response())


class TestUserFacingSurface:
    """An auth failure has to explain itself on the page, not just in JSON."""

    def _app(self):
        from weatherapp import create_app
        from weatherapp.config import Settings

        class FailingProvider:
            name = "weatherapi"

            def fetch(self, query, days=3):
                raise ProviderError(
                    "WeatherAPI rejected the key. Copy it again from "
                    "weatherapi.com/my-account - run 'python -m weatherapp.doctor'.",
                    status=401, kind="auth",
                )

            def search(self, query, limit=8):
                return []

        return create_app(settings=Settings(), provider=FailingProvider())

    def test_page_renders_the_remedy(self):
        client = self._app().test_client()
        response = client.get("/?q=London")
        body = response.get_data(as_text=True)
        assert response.status_code == 200, "the shell must still render, not 500"
        assert "weatherapi.com/my-account" in body
        assert "doctor" in body

    def test_api_reports_401_and_the_auth_kind(self):
        client = self._app().test_client()
        response = client.get("/api/v1/report?q=London")
        assert response.status_code == 401
        payload = response.get_json()
        assert payload["error"]["kind"] == "auth"
        assert "my-account" in payload["error"]["message"]
