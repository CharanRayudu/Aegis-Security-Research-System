"""Endpoint discovery helpers."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


class EndpointDiscovery:
    """Extract candidate API paths from HTTP responses."""

    URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
    PATH_PATTERN = re.compile(r"(?:(?<=\")|(?<=')|(?<=\s)|^)(/(?:api|rest|v1|v2|v3)[A-Za-z0-9\-._~/?=&%+]*)")

    def __init__(self, base_url: str) -> None:
        parsed = urlparse(base_url)
        self.base_netloc = parsed.netloc

    def discover_from_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        if response.get("status_code") == 0:
            return []

        discovered: dict[str, dict[str, Any]] = {}
        body = response.get("body")
        for value in self._walk(body):
            for candidate in self._extract_candidates(value):
                discovered.setdefault(
                    candidate,
                    {
                        "path": candidate,
                        "method": "GET",
                        "params": {},
                        "headers": {},
                        "body": {},
                        "source": "response_discovery",
                    },
                )
        return list(discovered.values())

    def _walk(self, value: Any) -> list[str]:
        items: list[str] = []
        if isinstance(value, dict):
            for key, nested in value.items():
                items.append(str(key))
                items.extend(self._walk(nested))
        elif isinstance(value, list):
            for nested in value:
                items.extend(self._walk(nested))
        elif value is not None:
            items.append(str(value))
        return items

    def _extract_candidates(self, text: str) -> set[str]:
        candidates: set[str] = set()
        for match in self.URL_PATTERN.findall(text):
            parsed = urlparse(match.rstrip(".,);"))
            if parsed.netloc == self.base_netloc and parsed.path.startswith("/"):
                candidates.add(parsed.path)
        for match in self.PATH_PATTERN.findall(text):
            normalized = match.rstrip(".,);").split("?", 1)[0].split("#", 1)[0]
            candidates.add(normalized)
        return candidates
