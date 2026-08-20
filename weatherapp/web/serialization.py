"""JSON responses with conditional-GET support."""

from __future__ import annotations

import hashlib
import json

from flask import Response, request

# Cache bookkeeping describes the transport, not the weather. Including it in
# the entity tag would change the tag on every request and defeat 304s.
VOLATILE_META = ("cached", "age_seconds", "generated_epoch")


def content_fingerprint(payload: dict) -> dict:
    """The payload minus fields that vary without the content varying."""
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return payload
    return {**payload, "meta": {k: v for k, v in meta.items() if k not in VOLATILE_META}}


def _dump(payload) -> str:
    return json.dumps(payload, separators=(",", ":"), default=str)


def json_response(payload, status: int = 200, max_age: int = 60,
                  private: bool = True, etag_over=None) -> Response:
    body = _dump(payload)
    source = body if etag_over is None else _dump(etag_over)
    etag = '"' + hashlib.sha256(source.encode("utf-8")).hexdigest()[:32] + '"'

    if status == 200 and request.headers.get("If-None-Match") == etag:
        response = Response(status=304)
    else:
        response = Response(body, status=status, mimetype="application/json")

    response.headers["ETag"] = etag
    scope = "private" if private else "public"
    response.headers["Cache-Control"] = f"{scope}, max-age={max_age}, stale-while-revalidate=120"
    response.headers["X-Content-Type-Options"] = "nosniff"

    meta = payload.get("meta") if isinstance(payload, dict) else None
    if isinstance(meta, dict) and "cached" in meta:
        response.headers["X-Cache"] = "HIT" if meta["cached"] else "MISS"
        response.headers["Age"] = str(int(meta.get("age_seconds") or 0))
    return response


def error_response(message: str, status: int = 400, kind: str = "request") -> Response:
    return json_response(
        {"error": {"message": message, "kind": kind, "status": status}}, status, max_age=0
    )
