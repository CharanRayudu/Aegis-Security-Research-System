"""HTTP client for autonomous endpoint testing."""

from __future__ import annotations

import time
from typing import Any

import requests
from requests import Response


class HttpExecutor:
    """Sends baseline and mutated HTTP requests with retries."""

    def __init__(
        self,
        base_url: str,
        default_headers: dict[str, str] | None = None,
        auth: dict[str, Any] | None = None,
        timeout: int = 15,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.auth = auth or {}
        self.timeout = timeout
        self.retries = retries

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _auth_headers(self) -> dict[str, str]:
        auth_type = self.auth.get("type")
        token = self.auth.get("token")
        if auth_type == "bearer" and token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _serialize_response(self, response: Response) -> dict[str, Any]:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
            "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            "url": str(response.url),
        }

    def send_request(
        self,
        path: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path)
        headers = {
            **self.default_headers,
            **self._auth_headers(),
            **(extra_headers or {}),
        }

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            print(f"[http] Attempt {attempt}/{self.retries} {method.upper()} {url}")
            try:
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=self.timeout,
                )
                serialized = self._serialize_response(response)
                print(
                    f"[http] Response {serialized['status_code']} in {serialized['elapsed_ms']}ms "
                    f"for {serialized['url']}"
                )
                return serialized
            except requests.RequestException as exc:
                last_error = exc
                print(f"[http] Request failed on attempt {attempt}: {exc}")
                if attempt < self.retries:
                    time.sleep(attempt)

        return {
            "status_code": 0,
            "headers": {},
            "body": {"error": str(last_error) if last_error else "unknown error"},
            "elapsed_ms": 0,
            "url": url,
        }
