"""HTML routes plus the legacy endpoints the previous version exposed."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for

from ..domain.protocols import ProviderError

pages = Blueprint("pages", __name__)


def _service():
    return current_app.extensions["barograph"]["service"]


def _settings():
    return current_app.extensions["barograph"]["settings"]


@pages.route("/", methods=["GET", "POST"])
def home():
    # The old UI posted a form; keep that working by turning it into a URL.
    if request.method == "POST":
        city = (request.form.get("city") or "").strip()
        return redirect(url_for("pages.home", q=city) if city else url_for("pages.home"))

    settings = _settings()
    query = (request.args.get("q") or settings.default_place).strip()
    initial, error = None, None
    try:
        initial = _service().report(query).to_dict()
    except ProviderError as exc:
        error = {"message": str(exc), "status": exc.status, "kind": exc.kind}

    return render_template(
        "index.html",
        initial_report=initial,
        initial_error=error,
        query=query,
        settings=settings,
    )


@pages.get("/sw.js")
def service_worker():
    # Must be served from the root for the worker to control the whole origin.
    response = send_from_directory(current_app.static_folder, "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@pages.get("/manifest.webmanifest")
def manifest():
    response = send_from_directory(current_app.static_folder, "manifest.webmanifest")
    response.headers["Content-Type"] = "application/manifest+json"
    return response


@pages.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "version": _settings().version})


@pages.get("/get_weather")
def legacy_get_weather():
    """The v1 endpoint. Kept because links and bookmarks to it exist."""
    city = (request.args.get("city") or "").strip()
    if not city:
        return jsonify({"error": "City is required"}), 400
    try:
        report = _service().report(city)
    except ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status

    current, place = report.current, report.place
    return jsonify({
        "location": {
            "name": place.name,
            "region": place.region,
            "country": place.country,
            "lat": place.lat,
            "lon": place.lon,
            "localtime": place.localtime_iso.replace("T", " "),
        },
        "current": {
            "temp_c": current.temp_c,
            "temp_f": round(current.temp_c * 9 / 5 + 32, 1),
            "condition": {"text": current.condition.text, "code": current.condition.code},
            "humidity": current.humidity,
            "wind_kph": current.wind_kph,
            "feelslike_c": current.feels_c,
            "air_quality": report.air.pollutants if report.air else None,
        },
    })
