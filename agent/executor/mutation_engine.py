"""Mutation engine for parameter tampering and basic fuzzing."""

from __future__ import annotations

from typing import Any


class MutationEngine:
    """Expands hypothesis-guided mutations with deterministic fuzzing."""

    BASIC_FUZZ_STRINGS = [
        "' OR '1'='1",
        "<script>alert(1)</script>",
        "../../../etc/passwd",
        "\"",
    ]

    def generate_mutations(
        self,
        endpoint: dict[str, Any],
        hypothesis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        base_mutations = [self._normalize_mutation(item, endpoint) for item in hypothesis.get("mutations", [])]
        generated: list[dict[str, Any]] = []

        params = endpoint.get("params") or {}
        body = endpoint.get("body") or {}

        if params:
            generated.extend(self._parameter_mutations(params))
        elif body:
            generated.extend(self._body_mutations(body))
        else:
            generated.append(
                {
                    "name": "probe_query_injection",
                    "description": "Inject a generic probe parameter when the endpoint has no declared inputs.",
                    "params": {"probe": self.BASIC_FUZZ_STRINGS[0]},
                    "headers": {"X-Research-Probe": "generic-probe"},
                    "body": endpoint.get("body") or {},
                }
            )

        deduped: dict[str, dict[str, Any]] = {}
        for mutation in base_mutations + generated:
            deduped.setdefault(mutation["name"], mutation)
        return list(deduped.values())

    def _normalize_mutation(self, mutation: dict[str, Any], endpoint: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": mutation["name"],
            "description": mutation.get("description", ""),
            "path": mutation.get("path", endpoint["path"]),
            "params": mutation.get("params", endpoint.get("params") or {}),
            "headers": mutation.get("headers", {}),
            "body": mutation.get("body", endpoint.get("body") or {}),
        }

    def _parameter_mutations(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        mutations: list[dict[str, Any]] = []
        for key, value in params.items():
            if isinstance(value, int):
                mutations.append(
                    {
                        "name": f"increment_param_{key}",
                        "description": f"Increment numeric parameter {key} to test object boundary access.",
                        "params": {**params, key: value + 1},
                        "headers": {},
                        "body": {},
                    }
                )
                mutations.append(
                    {
                        "name": f"large_param_{key}",
                        "description": f"Set {key} to a large integer to probe authorization and range handling.",
                        "params": {**params, key: 999999},
                        "headers": {},
                        "body": {},
                    }
                )
            else:
                for index, fuzz in enumerate(self.BASIC_FUZZ_STRINGS, start=1):
                    mutations.append(
                        {
                            "name": f"fuzz_param_{key}_{index}",
                            "description": f"Fuzz parameter {key} with crafted input #{index}.",
                            "params": {**params, key: fuzz},
                            "headers": {"X-Research-Probe": f"param-fuzz-{key}-{index}"},
                            "body": {},
                        }
                    )
        return mutations

    def _body_mutations(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        mutations: list[dict[str, Any]] = []
        for key, value in body.items():
            if isinstance(value, int):
                mutations.append(
                    {
                        "name": f"increment_body_{key}",
                        "description": f"Increment numeric body field {key}.",
                        "params": {},
                        "headers": {},
                        "body": {**body, key: value + 1},
                    }
                )
            else:
                for index, fuzz in enumerate(self.BASIC_FUZZ_STRINGS, start=1):
                    mutations.append(
                        {
                            "name": f"fuzz_body_{key}_{index}",
                            "description": f"Fuzz body field {key} with crafted input #{index}.",
                            "params": {},
                            "headers": {"X-Research-Probe": f"body-fuzz-{key}-{index}"},
                            "body": {**body, key: fuzz},
                        }
                    )
        return mutations
