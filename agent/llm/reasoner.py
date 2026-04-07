"""Generate IDOR-focused hypotheses for API endpoints."""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency path
    OpenAI = None


DEFAULT_MODEL = "gpt-4o-mini"
PLACEHOLDER_API_KEY = "OPENAI_API_KEY_HERE"


def generate_hypotheses(
    endpoint_data: dict[str, Any],
    memory_context: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    print(f"[reasoner] Generating IDOR hypotheses for {endpoint_data['method']} {endpoint_data['path']}")
    api_key = os.getenv("OPENAI_API_KEY", PLACEHOLDER_API_KEY)
    if api_key == PLACEHOLDER_API_KEY or OpenAI is None:
        print("[reasoner] Using local deterministic IDOR reasoning")
        return _local_hypotheses(endpoint_data, memory_context or [])

    prompt = (
        "You are an application security researcher focused only on IDOR and broken object-level authorization.\n"
        "Use the endpoint shape, inferred resource meaning, and local memory context.\n"
        "Return JSON only with a top-level key named hypotheses.\n"
        "hypotheses must be a list of 1 to 2 objects sorted by strongest first.\n\n"
        "Each object must contain:\n"
        "{\n"
        '  "name": "",\n'
        '  "hypothesis": "",\n'
        '  "test_cases": [],\n'
        '  "confidence": "",\n'
        '  "confidence_score": 0.0,\n'
        '  "resource_understanding": "",\n'
        '  "mutations": []\n'
        "}\n\n"
        "Rules:\n"
        "- Keep scope limited to IDOR only\n"
        "- confidence must be one of low, medium, high\n"
        "- mutations must only modify path or query identifiers\n"
        "- test_cases must describe practical baseline-vs-mutated authorization checks\n"
        "- Use memory to avoid repeating weak ideas\n\n"
        f"Endpoint data:\n{json.dumps(endpoint_data, indent=2)}\n\n"
        f"Memory context:\n{json.dumps(memory_context or [], indent=2)}"
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(model=DEFAULT_MODEL, input=prompt, temperature=0.1)
        parsed = json.loads(response.output_text.strip())
        hypotheses = parsed["hypotheses"]
        hypotheses.sort(key=lambda item: item.get("confidence_score", 0), reverse=True)
        return hypotheses
    except Exception as exc:
        print(f"[reasoner] OpenAI request failed: {exc}. Falling back to local IDOR reasoning")
        return _local_hypotheses(endpoint_data, memory_context or [])


def generate_hypothesis(
    endpoint_data: dict[str, Any],
    memory_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return generate_hypotheses(endpoint_data, memory_context or [])[0]


def _local_hypotheses(endpoint_data: dict[str, Any], memory_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = endpoint_data["path"]
    method = endpoint_data.get("method", "GET")
    params = endpoint_data.get("params") or {}
    resource = endpoint_data.get("resource") or _resource_from_path(path)
    path_mutations = _path_mutations(path, params)
    query_mutations = _query_mutations(path, params)
    memory_summary = _memory_summary(memory_context)
    has_identifier = bool(path_mutations or query_mutations)

    primary = {
        "name": "idor_identifier_replay",
        "hypothesis": (
            f"{method} {path} may expose another {resource} record when object identifiers are changed. "
            f"Prior related context: {memory_summary}"
        ),
        "test_cases": [
            "Send a baseline request to the configured object identifier.",
            "Replay the request with nearby identifier values and compare authorization behavior.",
            "Check whether the mutated response returns another object's data with a similar schema.",
        ],
        "confidence": "high" if has_identifier else "medium",
        "confidence_score": 0.84 if has_identifier else 0.62,
        "resource_understanding": f"The endpoint appears to operate on the '{resource}' resource.",
        "mutations": path_mutations[:2] + query_mutations[:2],
    }

    secondary = {
        "name": "idor_sparse_identifier_enumeration",
        "hypothesis": (
            f"{method} {path} may allow access to high-value or sparse {resource} identifiers without ownership checks. "
            f"Prior related context: {memory_summary}"
        ),
        "test_cases": [
            "Try a distant identifier such as 999999 and compare status code and response body size.",
            "Treat unchanged denial responses as not confirmed rather than positive findings.",
        ],
        "confidence": "medium" if has_identifier else "low",
        "confidence_score": 0.67 if has_identifier else 0.4,
        "resource_understanding": f"The final path segments suggest a direct object lookup for '{resource}'.",
        "mutations": _high_value_mutations(path, params),
    }

    hypotheses = [primary]
    if secondary["mutations"]:
        hypotheses.append(secondary)
    return hypotheses


def _path_mutations(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    segments = path.split("/")
    for index in range(len(segments) - 1, -1, -1):
        if not segments[index].isdigit():
            continue
        current = int(segments[index])
        mutations = []
        for new_value, label in [(current + 1, "increment"), (max(current - 1, 0), "decrement")]:
            updated = list(segments)
            updated[index] = str(new_value)
            mutations.append(
                {
                    "name": f"path_{label}_{new_value}",
                    "description": f"Replace path identifier with {new_value}.",
                    "path": "/".join(updated),
                    "params": params,
                    "headers": {},
                    "body": {},
                }
            )
        return mutations
    return []


def _high_value_mutations(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    mutations: list[dict[str, Any]] = []
    path_segments = path.split("/")
    for index in range(len(path_segments) - 1, -1, -1):
        if path_segments[index].isdigit():
            updated = list(path_segments)
            updated[index] = "999999"
            mutations.append(
                {
                    "name": "path_high_value_999999",
                    "description": "Replace path identifier with a distant high value.",
                    "path": "/".join(updated),
                    "params": params,
                    "headers": {},
                    "body": {},
                }
            )
            break

    for key, value in params.items():
        if _looks_like_identifier(key) and (isinstance(value, int) or (isinstance(value, str) and value.isdigit())):
            updated = dict(params)
            updated[key] = 999999
            mutations.append(
                {
                    "name": f"query_{key}_high_value_999999",
                    "description": f"Replace query identifier {key} with 999999.",
                    "path": path,
                    "params": updated,
                    "headers": {},
                    "body": {},
                }
            )
    return mutations


def _query_mutations(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    mutations: list[dict[str, Any]] = []
    for key, value in params.items():
        if not _looks_like_identifier(key):
            continue
        numeric = _numeric_value(value)
        if numeric is None:
            continue
        for new_value, label in [(numeric + 1, "increment"), (max(numeric - 1, 0), "decrement")]:
            updated = dict(params)
            updated[key] = new_value
            mutations.append(
                {
                    "name": f"query_{key}_{label}_{new_value}",
                    "description": f"Replace query identifier {key} with {new_value}.",
                    "path": path,
                    "params": updated,
                    "headers": {},
                    "body": {},
                }
            )
    return mutations


def _memory_summary(memory_context: list[dict[str, Any]]) -> str:
    if not memory_context:
        return "no related prior runs"
    fragments = []
    for item in memory_context[:3]:
        fragments.append(item.get("label", item.get("type", "record")))
    return ", ".join(fragments)


def _resource_from_path(path: str) -> str:
    segments = [segment for segment in path.split("/") if segment]
    for segment in reversed(segments):
        lowered = segment.lower()
        if segment.isdigit() or lowered in {"api", "rest", "v1", "v2", "v3"}:
            continue
        return segment
    return "resource"


def _looks_like_identifier(key: str) -> bool:
    lowered = key.lower()
    return lowered == "id" or lowered.endswith("_id") or lowered.endswith("id")


def _numeric_value(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
