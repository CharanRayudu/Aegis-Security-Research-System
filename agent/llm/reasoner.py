"""Generate security hypotheses for API endpoints."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-mini"
PLACEHOLDER_API_KEY = "OPENAI_API_KEY_HERE"


def _local_hypotheses(
    endpoint_data: dict[str, Any],
    memory_context: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    path = endpoint_data["path"]
    method = endpoint_data.get("method", "GET")
    params = endpoint_data.get("params") or {}
    body = endpoint_data.get("body") or {}
    resource = endpoint_data.get("resource") or _resource_from_path(path)
    has_inputs = bool(params or body)
    memory_context = memory_context or []

    confidence_bias = min(len(memory_context) * 0.02, 0.08)
    memory_summary = _summarize_memory(memory_context)

    hypotheses = [
        {
            "name": "authorization_bypass",
            "confidence": _confidence_string(min((0.82 if "user" in path or "admin" in path else 0.63) + confidence_bias, 0.95)),
            "confidence_score": min((0.82 if "user" in path or "admin" in path else 0.63) + confidence_bias, 0.95),
            "risk_summary": "Access-control flaws often appear around direct object references.",
            "hypothesis": (
                f"{method} {path} may expose unauthorized {resource} data when identifiers or trust headers are changed. "
                f"Memory context: {memory_summary}"
            ),
            "test_cases": [
                "Replay the request without authorization headers.",
                "Spoof user identity headers and compare authorization boundaries.",
            ],
            "mutations": [
                {
                    "name": "unauthenticated_request",
                    "description": "Replay the request without authorization material.",
                    "params": params,
                    "headers": {"Authorization": ""},
                    "body": body,
                },
                {
                    "name": "header_role_spoof",
                    "description": "Inject role-oriented headers to probe trust in client claims.",
                    "params": params,
                    "headers": {"X-Forwarded-User": "admin", "X-Original-User": "admin"},
                    "body": body,
                },
            ],
        },
        {
            "name": "input_validation_weakness",
            "confidence": _confidence_string(min((0.71 if has_inputs else 0.52) + confidence_bias, 0.9)),
            "confidence_score": min((0.71 if has_inputs else 0.52) + confidence_bias, 0.9),
            "risk_summary": "Weak validation may produce differential behavior across malformed input.",
            "hypothesis": (
                f"{method} {path} may process malformed {resource} inputs inconsistently and leak validation behavior. "
                f"Memory context: {memory_summary}"
            ),
            "test_cases": [
                "Inject metacharacters into parameters and compare body structure.",
                "Observe response size or error detail growth under malformed input.",
            ],
            "mutations": [
                {
                    "name": "input_pollution",
                    "description": "Inject metacharacters to detect parser inconsistencies.",
                    "params": {**params, "probe": "' OR '1'='1"},
                    "headers": {"X-Research-Probe": "input-pollution"},
                    "body": body,
                }
            ],
        },
        {
            "name": "identifier_enumeration",
            "confidence": _confidence_string(
                min((0.68 if any(token.isdigit() for token in path.split("/")) else 0.48) + confidence_bias, 0.88)
            ),
            "confidence_score": min(
                (0.68 if any(token.isdigit() for token in path.split("/")) else 0.48) + confidence_bias,
                0.88,
            ),
            "risk_summary": "Sequential identifiers can expose object enumeration or boundary conditions.",
            "hypothesis": (
                f"{method} {path} may allow adjacent {resource} enumeration when nearby identifiers are requested. "
                f"Memory context: {memory_summary}"
            ),
            "test_cases": [
                "Increment the path identifier and compare status and response size.",
                "Check whether adjacent objects expose similar schemas or leaked data.",
            ],
            "mutations": [
                {
                    "name": "path_id_increment",
                    "description": "Request an adjacent identifier in the path when present.",
                    "path": _increment_path_identifier(path),
                    "params": params,
                    "headers": {},
                    "body": body,
                }
            ],
        },
    ]
    return sorted(hypotheses, key=lambda item: item["confidence_score"], reverse=True)


def _increment_path_identifier(path: str) -> str:
    segments = path.split("/")
    for index in range(len(segments) - 1, -1, -1):
        if segments[index].isdigit():
            segments[index] = str(int(segments[index]) + 1)
            return "/".join(segments)
    return path


def _resource_from_path(path: str) -> str:
    segments = [segment for segment in path.split("/") if segment]
    for segment in reversed(segments):
        lowered = segment.lower()
        if segment.isdigit() or lowered in {"api", "rest", "v1", "v2", "v3"}:
            continue
        return segment
    return "resource"


def _confidence_string(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _summarize_memory(memory_context: list[dict[str, Any]]) -> str:
    if not memory_context:
        return "no prior related history"

    labels = []
    for item in memory_context[:4]:
        labels.append(f"{item.get('type', 'record')}:{item.get('label', item.get('timestamp', 'unknown'))}")
    return "; ".join(labels)


def generate_hypotheses(
    endpoint_data: dict[str, Any],
    memory_context: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate multiple ranked security hypotheses for a target endpoint."""

    print(f"[reasoner] Generating ranked hypotheses for {endpoint_data['method']} {endpoint_data['path']}")
    api_key = os.getenv("OPENAI_API_KEY", PLACEHOLDER_API_KEY)
    if api_key == PLACEHOLDER_API_KEY:
        print("[reasoner] Placeholder API key detected, using local ranked hypotheses")
        return _local_hypotheses(endpoint_data, memory_context=memory_context)

    prompt = (
        "You are a security research assistant. Analyze the API endpoint using local memory context, the endpoint "
        "shape, and the underlying resource semantics inferred from the path. Return JSON only with a top-level key "
        "named hypotheses. hypotheses must be a list of exactly 3 objects sorted by confidence descending.\n\n"
        "Each hypothesis object must contain:\n"
        "- name\n"
        "- hypothesis\n"
        "- test_cases\n"
        "- confidence\n"
        "- confidence_score\n"
        "- risk_summary\n"
        "- mutations\n\n"
        "Constraints:\n"
        "- confidence must be one of: low, medium, high\n"
        "- confidence_score must be a numeric score between 0 and 1\n"
        "- test_cases must be a list of concrete checks the executor can run\n"
        "- mutations must be a list of 1 to 4 objects with keys: name, description, path, params, headers, body\n"
        "- Use past memory to reduce repetition and false positives\n"
        "- Prefer hypotheses that are supported by status differences, response-size differences, or likely data leakage patterns\n\n"
        f"Endpoint data:\n{json.dumps(endpoint_data, indent=2)}"
        f"\n\nRelevant local memory:\n{json.dumps(memory_context or [], indent=2)}"
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=DEFAULT_MODEL,
            input=prompt,
            temperature=0.15,
        )
        content = response.output_text.strip()
        parsed = json.loads(content)
        hypotheses = parsed["hypotheses"]
        hypotheses.sort(key=lambda item: item.get("confidence_score", 0), reverse=True)
        print("[reasoner] Ranked hypotheses generated via OpenAI API")
        return hypotheses
    except Exception as exc:
        print(f"[reasoner] OpenAI request failed: {exc}. Falling back to local ranked hypotheses")
        return _local_hypotheses(endpoint_data, memory_context=memory_context)


def generate_hypothesis(
    endpoint_data: dict[str, Any],
    memory_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the highest-confidence hypothesis for compatibility with existing callers."""

    return generate_hypotheses(endpoint_data, memory_context=memory_context)[0]
