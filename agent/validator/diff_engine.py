"""Response diffing and finding detection."""

from __future__ import annotations

import json
import re
from typing import Any


class DiffEngine:
    """Compares baseline and mutated responses with conservative scoring."""

    LEAKAGE_PATTERNS = [
        re.compile(r"\bpassword\b", re.IGNORECASE),
        re.compile(r"\bsecret\b", re.IGNORECASE),
        re.compile(r"\btoken\b", re.IGNORECASE),
        re.compile(r"\bssn\b", re.IGNORECASE),
        re.compile(r"\bemail\b", re.IGNORECASE),
        re.compile(r"\bapi[_-]?key\b", re.IGNORECASE),
    ]

    def compare(
        self,
        baseline: dict[str, Any],
        candidate: dict[str, Any],
        mutation: dict[str, Any],
        hypothesis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if baseline.get("status_code") == 0 or candidate.get("status_code") == 0:
            return {
                "mutation_name": mutation.get("name"),
                "hypothesis_name": (hypothesis or {}).get("name"),
                "is_interesting": False,
                "severity": "informational",
                "status_changed": baseline.get("status_code") != candidate.get("status_code"),
                "headers_changed": baseline.get("headers") != candidate.get("headers"),
                "body_changed": self._canonicalize(baseline.get("body")) != self._canonicalize(candidate.get("body")),
                "response_size_changed": False,
                "data_leakage_detected": False,
                "baseline_status": baseline.get("status_code"),
                "candidate_status": candidate.get("status_code"),
                "baseline_size": self._response_size(baseline),
                "candidate_size": self._response_size(candidate),
                "reasons": ["Transport error prevented reliable comparison"],
            }

        status_changed = baseline.get("status_code") != candidate.get("status_code")
        headers_changed = baseline.get("headers") != candidate.get("headers")
        baseline_body = self._canonicalize(baseline.get("body"))
        candidate_body = self._canonicalize(candidate.get("body"))
        body_changed = baseline_body != candidate_body

        baseline_size = self._response_size(baseline)
        candidate_size = self._response_size(candidate)
        size_delta = abs(candidate_size - baseline_size)
        size_ratio = (size_delta / max(baseline_size, 1)) if baseline_size else float(candidate_size > 0)
        response_size_changed = size_delta >= 40 and size_ratio >= 0.2

        baseline_leaks = self._detect_leakage(baseline_body)
        candidate_leaks = self._detect_leakage(candidate_body)
        new_leaks = sorted(candidate_leaks - baseline_leaks)
        data_leakage_detected = bool(new_leaks)

        severity = "informational"
        reasons: list[str] = []

        if status_changed:
            reasons.append("HTTP status changed")
        if response_size_changed:
            reasons.append(f"Response size changed from {baseline_size} to {candidate_size} bytes")
        if data_leakage_detected:
            reasons.append(f"Potential data leakage patterns detected: {', '.join(new_leaks)}")
        if headers_changed and (status_changed or response_size_changed or data_leakage_detected):
            reasons.append("Response headers also changed")

        if status_changed and candidate.get("status_code") == 200 and baseline.get("status_code") in {401, 403, 404}:
            severity = "high"
            reasons.append("Mutated request produced an unexpectedly successful response")
        elif data_leakage_detected:
            severity = "high"
        elif status_changed and response_size_changed:
            severity = "medium"
        elif body_changed and response_size_changed:
            severity = "medium"
        elif status_changed and baseline.get("status_code") >= 500 > candidate.get("status_code", 0):
            severity = "medium"
            reasons.append("Mutation materially changed server error behavior")
        else:
            severity = "informational"

        is_interesting = severity in {"medium", "high"}

        return {
            "mutation_name": mutation.get("name"),
            "hypothesis_name": (hypothesis or {}).get("name"),
            "hypothesis_confidence": (hypothesis or {}).get("confidence"),
            "is_interesting": is_interesting,
            "severity": severity,
            "status_changed": status_changed,
            "headers_changed": headers_changed,
            "body_changed": body_changed,
            "response_size_changed": response_size_changed,
            "data_leakage_detected": data_leakage_detected,
            "new_leakage_patterns": new_leaks,
            "baseline_status": baseline.get("status_code"),
            "candidate_status": candidate.get("status_code"),
            "baseline_size": baseline_size,
            "candidate_size": candidate_size,
            "reasons": reasons or ["No strong signal beyond normal variation"],
        }

    def _canonicalize(self, body: Any) -> str:
        if isinstance(body, (dict, list)):
            return json.dumps(body, sort_keys=True, ensure_ascii=True)
        return str(body)

    def _response_size(self, response: dict[str, Any]) -> int:
        return len(self._canonicalize(response.get("body")))

    def _detect_leakage(self, body_text: str) -> set[str]:
        matches: set[str] = set()
        for pattern in self.LEAKAGE_PATTERNS:
            if pattern.search(body_text):
                matches.add(pattern.pattern)
        return matches
