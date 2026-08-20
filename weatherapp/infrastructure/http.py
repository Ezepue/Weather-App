"""HTTP with one retry and errors translated into the domain's language."""

from __future__ import annotations

import time

import requests

from ..domain.protocols import ProviderError


class HttpClient:
    def __init__(self, timeout: float = 8.0, retries: int = 1, backoff: float = 0.4):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._session = requests.Session()

    def get_json(self, url: str, params: dict | None = None) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self.timeout)
            except requests.exceptions.Timeout as exc:
                last_error = exc
                message, status = "Upstream timed out", 504
            except requests.exceptions.RequestException as exc:
                last_error = exc
                message, status = "Could not reach the weather service", 502
            else:
                return self._decode(response)

            if attempt < self.retries:
                time.sleep(self.backoff * (attempt + 1))
        raise ProviderError(message, status=status, kind="network") from last_error

    @staticmethod
    def _decode(response) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("Upstream sent a malformed response", 502, "decode") from exc

        # WeatherAPI reports its own errors inside a 200-or-4xx JSON envelope.
        if isinstance(payload, dict) and "error" in payload:
            error = payload["error"] or {}
            code = error.get("code")
            message = error.get("message") or "Upstream rejected the request"
            # 1006 is "no matching location", which is the user's input, not a fault.
            status = 404 if code == 1006 else (401 if code in (1002, 2006, 2008) else 400)
            raise ProviderError(message, status=status, kind="upstream")

        if response.status_code >= 500:
            raise ProviderError("Weather service is having problems", 502, "upstream")
        if response.status_code >= 400:
            raise ProviderError("Weather service rejected the request", 400, "upstream")
        return payload
