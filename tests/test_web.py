"""The HTTP surface, including the endpoints the previous version exposed."""

import json

import pytest

from weatherapp.domain.protocols import ProviderError


class TestReportEndpoint:
    def test_returns_the_full_schema(self, client):
        payload = client.get("/api/v1/report?q=London").get_json()
        assert set(payload) == {"meta", "place", "current", "hourly", "daily",
                               "astro", "air", "marine", "alerts", "advice"}

    def test_defaults_to_the_configured_place(self, client):
        assert client.get("/api/v1/report").get_json()["place"]["name"] == "London"

    def test_accepts_coordinates(self, client):
        payload = client.get("/api/v1/report?q=35.68,139.65").get_json()
        assert payload["place"]["lat"] == pytest.approx(35.68)

    def test_clamps_the_day_count(self, client):
        assert len(client.get("/api/v1/report?q=London&days=99").get_json()["daily"]) == 10
        assert len(client.get("/api/v1/report?q=London&days=0").get_json()["daily"]) == 1

    def test_ignores_a_nonsense_day_count(self, client):
        assert client.get("/api/v1/report?q=London&days=abc").status_code == 200

    def test_rejects_an_absurd_query(self, client):
        response = client.get(f"/api/v1/report?q={'x' * 200}")
        assert response.status_code == 400
        assert response.get_json()["error"]["kind"] == "request"

    def test_serves_json_content_type(self, client):
        assert client.get("/api/v1/report?q=London").mimetype == "application/json"


class TestConditionalGet:
    def test_etag_is_returned(self, client):
        assert client.get("/api/v1/report?q=London").headers["ETag"].startswith('"')

    def test_matching_etag_yields_304(self, client):
        first = client.get("/api/v1/report?q=London")
        second = client.get("/api/v1/report?q=London", headers={"If-None-Match": first.headers["ETag"]})
        assert second.status_code == 304
        assert second.get_data() == b""

    def test_mismatched_etag_yields_the_body(self, client):
        response = client.get("/api/v1/report?q=London", headers={"If-None-Match": '"nope"'})
        assert response.status_code == 200

    def test_cache_state_does_not_change_the_etag(self, client):
        """A cache hit is transport, not content; it must not bust the tag."""
        first = client.get("/api/v1/report?q=Oslo")
        second = client.get("/api/v1/report?q=Oslo")
        assert first.headers["X-Cache"] == "MISS"
        assert second.headers["X-Cache"] == "HIT"
        assert first.headers["ETag"] == second.headers["ETag"]

    def test_cache_headers_are_present(self, client):
        headers = client.get("/api/v1/report?q=London").headers
        assert "max-age" in headers["Cache-Control"]
        assert "Age" in headers


class TestSearchEndpoint:
    def test_finds_places(self, client):
        results = client.get("/api/v1/search?q=lond").get_json()["results"]
        assert any(r["name"] == "London" for r in results)

    def test_empty_query_returns_nothing(self, client):
        assert client.get("/api/v1/search?q=").get_json()["results"] == []

    def test_limit_is_capped(self, client):
        assert len(client.get("/api/v1/search?q=a&limit=999").get_json()["results"]) <= 12

    def test_bad_limit_is_tolerated(self, client):
        assert client.get("/api/v1/search?q=lo&limit=abc").status_code == 200


class TestCompareEndpoint:
    def test_compares_two_places(self, client):
        reports = client.get("/api/v1/compare?q=London&q=Cairo").get_json()["reports"]
        assert len(reports) == 2
        assert {r["place"]["name"] for r in reports} == {"London", "Cairo"}

    def test_requires_two(self, client):
        assert client.get("/api/v1/compare?q=London").status_code == 400

    def test_caps_the_number_compared(self, client):
        response = client.get("/api/v1/compare?" + "&".join(f"q=City{i}" for i in range(9)))
        assert len(response.get_json()["reports"]) <= 4


class TestMetaEndpoints:
    def test_capabilities_lists_activities(self, client):
        payload = client.get("/api/v1/capabilities").get_json()
        assert payload["demo"] is True
        assert "running" in payload["activities"]

    def test_healthz_reports_cache_stats(self, client):
        payload = client.get("/api/v1/healthz").get_json()
        assert payload["status"] == "ok"
        assert "entries" in payload["cache"]

    def test_root_healthz(self, client):
        assert client.get("/healthz").get_json()["status"] == "ok"


class TestPage:
    def test_renders_with_an_embedded_report(self, client):
        body = client.get("/?q=Tokyo").get_data(as_text=True)
        assert "Barograph" in body
        assert 'id="initial-report"' in body
        assert "Tokyo" in body

    def test_embedded_report_is_valid_json(self, client):
        body = client.get("/?q=Tokyo").get_data(as_text=True)
        raw = body.split('id="initial-report" type="application/json">')[1].split("</script>")[0]
        assert json.loads(raw)["place"]["name"] == "Tokyo"

    def test_form_post_becomes_a_url(self, client):
        response = client.post("/", data={"city": "Berlin"})
        assert response.status_code == 302
        assert "q=Berlin" in response.headers["Location"]

    def test_empty_form_post_does_not_break(self, client):
        assert client.post("/", data={"city": ""}).status_code == 302

    def test_service_worker_is_served_from_the_root(self, client):
        response = client.get("/sw.js")
        assert response.status_code == 200
        assert response.headers["Service-Worker-Allowed"] == "/"

    def test_manifest_content_type(self, client):
        assert client.get("/manifest.webmanifest").headers["Content-Type"] == "application/manifest+json"

    def test_security_headers(self, client):
        headers = client.get("/?q=London").headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


class TestLegacyEndpoint:
    def test_keeps_the_v1_shape(self, client):
        payload = client.get("/get_weather?city=Paris").get_json()
        assert payload["location"]["name"] == "Paris"
        assert "temp_c" in payload["current"]
        assert "temp_f" in payload["current"]
        assert "condition" in payload["current"]

    def test_still_requires_a_city(self, client):
        response = client.get("/get_weather")
        assert response.status_code == 400
        assert response.get_json()["error"] == "City is required"


class TestErrorHandling:
    def test_unknown_path_is_json(self, client):
        response = client.get("/nope")
        assert response.status_code == 404
        assert response.get_json()["error"]

    def test_provider_failure_becomes_the_right_status(self, app, monkeypatch):
        service = app.extensions["barograph"]["service"]

        def explode(*_args, **_kwargs):
            raise ProviderError("no matching location", status=404, kind="upstream")

        monkeypatch.setattr(service, "report", explode)
        response = app.test_client().get("/api/v1/report?q=Atlantis")
        assert response.status_code == 404
        assert response.get_json()["error"]["kind"] == "upstream"
