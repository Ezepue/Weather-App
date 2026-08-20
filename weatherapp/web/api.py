"""The JSON API. Every route is a thin translation of a service call."""

from __future__ import annotations

from flask import Blueprint, current_app, request

from ..domain.protocols import ProviderError
from .serialization import content_fingerprint, error_response, json_response

api = Blueprint("api", __name__, url_prefix="/api/v1")

MAX_COMPARE = 4


def _service():
    return current_app.extensions["barograph"]["service"]


def _settings():
    return current_app.extensions["barograph"]["settings"]


def _days() -> int:
    try:
        days = int(request.args.get("days", _settings().forecast_days))
    except (TypeError, ValueError):
        days = _settings().forecast_days
    return max(1, min(10, days))


@api.errorhandler(ProviderError)
def _provider_error(exc: ProviderError):
    return error_response(str(exc), exc.status, exc.kind)


@api.get("/report")
def report():
    query = (request.args.get("q") or "").strip()
    if not query:
        query = _settings().default_place
    if len(query) > 120:
        return error_response("Place name is too long", 400, "request")
    try:
        result = _service().report(query, _days())
    except ProviderError as exc:
        return error_response(str(exc), exc.status, exc.kind)
    payload = result.to_dict()
    return json_response(payload, max_age=60, etag_over=content_fingerprint(payload))


@api.get("/search")
def search():
    query = (request.args.get("q") or "").strip()
    if not query:
        return json_response({"results": []}, max_age=0)
    try:
        limit = max(1, min(12, int(request.args.get("limit", 8))))
    except (TypeError, ValueError):
        limit = 8
    try:
        results = _service().search(query, limit)
    except ProviderError as exc:
        return error_response(str(exc), exc.status, exc.kind)
    return json_response({"results": results}, max_age=600)


@api.get("/compare")
def compare():
    queries = [q.strip() for q in request.args.getlist("q") if q.strip()][:MAX_COMPARE]
    if len(queries) < 2:
        return error_response("Give at least two q parameters to compare", 400, "request")
    try:
        reports = _service().compare(queries, _days())
    except ProviderError as exc:
        return error_response(str(exc), exc.status, exc.kind)
    return json_response({"reports": [r.to_dict() for r in reports]}, max_age=60)


@api.get("/capabilities")
def capabilities():
    settings = _settings()
    return json_response({
        "version": settings.version,
        "provider": settings.active_provider,
        "demo": not settings.live,
        "forecast_days": settings.forecast_days,
        "marine": settings.marine_enabled,
        "activities": [s.key for s in _activity_keys()],
    }, max_age=300)


def _activity_keys():
    from ..advice import all_scorers
    return all_scorers()


@api.get("/healthz")
def healthz():
    provider = current_app.extensions["barograph"]["provider"]
    stats = provider.stats() if hasattr(provider, "stats") else {}
    settings = _settings()
    return json_response({
        "status": "ok",
        "provider": settings.active_provider,
        "version": settings.version,
        "cache": stats,
        # Enough to diagnose a key problem on a host where the CLI cannot be
        # run. Deliberately excludes the value, masked or otherwise: this
        # endpoint is public.
        "key": {
            "configured": bool(settings.api_key),
            "status": settings.key_status,
            "source": settings.key_source or None,
            "length": len(settings.api_key),
            "normalised": list(settings.key_repairs),
        },
    }, max_age=0)
