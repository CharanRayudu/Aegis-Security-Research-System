"""Mutation engine for IDOR-style identifier mutation."""

from __future__ import annotations

from typing import Any


class MutationEngine:
    """Builds a small deterministic set of IDOR-oriented mutations."""

    def generate_mutations(
        self,
        endpoint: dict[str, Any],
        hypothesis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        mutations: list[dict[str, Any]] = []
        mutations.extend(self._normalize_mutations(hypothesis.get("mutations", []), endpoint))
        mutations.extend(self._path_identifier_mutations(endpoint))
        mutations.extend(self._query_identifier_mutations(endpoint))
        return self._dedupe(mutations)

    def _normalize_mutations(
        self,
        source_mutations: list[dict[str, Any]],
        endpoint: dict[str, Any],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for mutation in source_mutations:
            normalized.append(
                {
                    "name": mutation["name"],
                    "description": mutation.get("description", ""),
                    "path": mutation.get("path", endpoint["path"]),
                    "params": mutation.get("params", endpoint.get("params") or {}),
                    "headers": mutation.get("headers", {}),
                    "body": mutation.get("body", endpoint.get("body") or {}),
                }
            )
        return normalized

    def _path_identifier_mutations(self, endpoint: dict[str, Any]) -> list[dict[str, Any]]:
        path = endpoint["path"]
        segments = path.split("/")
        mutations: list[dict[str, Any]] = []

        for index in range(len(segments) - 1, -1, -1):
            if not segments[index].isdigit():
                continue

            current_value = int(segments[index])
            for label, new_value in [
                ("increment", current_value + 1),
                ("decrement", max(current_value - 1, 0)),
                ("high_value", 999999),
            ]:
                updated = list(segments)
                updated[index] = str(new_value)
                mutations.append(
                    {
                        "name": f"path_{label}_{new_value}",
                        "description": f"Replace path identifier {current_value} with {new_value}.",
                        "path": "/".join(updated),
                        "params": endpoint.get("params") or {},
                        "headers": {},
                        "body": endpoint.get("body") or {},
                    }
                )
            break

        return mutations

    def _query_identifier_mutations(self, endpoint: dict[str, Any]) -> list[dict[str, Any]]:
        params = endpoint.get("params") or {}
        mutations: list[dict[str, Any]] = []

        for key, value in params.items():
            normalized_value = self._extract_numeric(value)
            if normalized_value is None or not self._looks_like_identifier(key):
                continue

            for label, new_value in [
                ("increment", normalized_value + 1),
                ("decrement", max(normalized_value - 1, 0)),
                ("high_value", 999999),
            ]:
                updated = dict(params)
                updated[key] = new_value
                mutations.append(
                    {
                        "name": f"query_{key}_{label}_{new_value}",
                        "description": f"Modify query identifier {key} from {normalized_value} to {new_value}.",
                        "path": endpoint["path"],
                        "params": updated,
                        "headers": {},
                        "body": endpoint.get("body") or {},
                    }
                )

        return mutations

    def _extract_numeric(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _looks_like_identifier(self, key: str) -> bool:
        lowered = key.lower()
        return lowered == "id" or lowered.endswith("_id") or lowered.endswith("id")

    def _dedupe(self, mutations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for mutation in mutations:
            signature = (
                mutation["name"],
                mutation.get("path"),
                str(sorted((mutation.get("params") or {}).items())),
            )
            deduped.setdefault(str(signature), mutation)
        return list(deduped.values())
