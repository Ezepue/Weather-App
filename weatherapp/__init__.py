"""Barograph - application factory.

Composition happens here and nowhere else: this is the only place that knows
which concrete provider, clock and cache the running application uses.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from .config import Settings
from .domain.protocols import ProviderError
from .infrastructure.clock import SystemClock
from .providers import build_provider
from .services import ReportService
from .web.api import api
from .web.pages import pages

__all__ = ["create_app", "Settings"]


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_environment() -> Path | None:
    """Load .env from the project root.

    A relative path resolves against the working directory, so running from
    anywhere but the repo root silently produced a keyless app. override=True
    because when someone edits .env they mean it to win over a stale export.
    """
    env_file = PROJECT_ROOT / ".env"
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file, override=True)
        return env_file
    load_dotenv(override=False)
    return None


def create_app(settings: Settings | None = None, provider=None, clock=None) -> Flask:
    load_environment()
    settings = settings or Settings.from_env()
    clock = clock or SystemClock()
    provider = provider or build_provider(settings, clock)

    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config["JSON_SORT_KEYS"] = False
    app.config["SETTINGS"] = settings
    app.extensions["barograph"] = {
        "settings": settings,
        "clock": clock,
        "provider": provider,
        "service": ReportService(provider, clock, settings),
    }

    app.register_blueprint(api)
    app.register_blueprint(pages)
    _register_error_handlers(app)

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return response

    return app


def _register_error_handlers(app: Flask) -> None:
    def wants_json() -> bool:
        return request.path.startswith("/api/") or "application/json" in (request.headers.get("Accept") or "")

    @app.errorhandler(ProviderError)
    def _provider_error(exc: ProviderError):
        if wants_json():
            return jsonify({"error": {"message": str(exc), "kind": exc.kind, "status": exc.status}}), exc.status
        return jsonify({"error": str(exc)}), exc.status

    @app.errorhandler(404)
    def _not_found(_exc):
        if wants_json():
            return jsonify({"error": {"message": "Not found", "kind": "request", "status": 404}}), 404
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def _server_error(_exc):
        app.logger.exception("Unhandled error")
        return jsonify({"error": {"message": "Internal error", "kind": "server", "status": 500}}), 500
