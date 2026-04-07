"""Response diffing and finding detection for IDOR validation."""

from __future__ import annotations

import json
import re
from typing import Any


class DiffEngine:
    """Compares baseline and mutated responses for IDOR-specific signals."""

    LEAKAGE_PATTERNS = [
        re.compile(r"\bemail\b", re.IGNORECASE),
        re.compile(r"\btoken\b", re.IGNORECASE),
        re.compile(r"\bpassword\b", re.IGNORECASE),
        re.compile(r"\bsecret\b", re.IGNORECASE),
        re.compile(r"\bssn\b", re.IGNORECASE),
    ]

    def compare(
        self,
        baseline: dict[str, Any],
        candidate: dict[str, Any],
        mutation: dict[str, Any],
        hypothesis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        baseline_body = self._canonicalize(baseline.get("body"))
        candidate_body = self._canonicalize(candidate.get("body"))
        baseline_size = len(baseline_body)
        candidate_size = len(candidate_body)
        status_changed = baseline.get("status_code") != candidate.get("status_code")
        body_changed = baseline_body != candidate_body
        response_size_changed = abs(candidate_size - baseline_size) >= 40
        new_leaks = sorted(self._detect_leakage(candidate_body) - self._detect_leakage(baseline_body))
        data_leakage_detected = bool(new_leaks)

        reasons: list[str] = []
        if baseline.get("status_code") == 0 or candidate.get("status_code") == 0:
            reasons.append("Transport failure prevented a reliable authorization comparison")
            decision = "Inconclusive"
        elif baseline.get("status_code") in {401, 403, 404} and candidate.get("status_code", 0) in range(200, 300):
            decision = "Confirmed"
            reasons.append("Mutated identifier succeeded where baseline was denied")
        elif status_changed and candidate.get("status_code", 0) in range(200, 300) and (response_size_changed or data_leakage_detected):
            decision = "Confirmed"
            reasons.append("Mutated identifier changed authorization outcome and returned materially different data")
        elif baseline.get("status_code") == candidate.get("status_code") and not body_changed and not data_leakage_detected:
            decision = "Not Confirmed"
            reasons.append("Mutated identifier behaved like baseline")
        elif data_leakage_detected and candidate.get("status_code", 0) in range(200, 300):
            decision = "Confirmed"
            reasons.append("Mutated identifier introduced possible sensitive fields")
        else:
            decision = "Inconclusive"
            reasons.append("Behavior changed, but evidence is insufficient for a confident IDOR conclusion")

        if status_changed:
            reasons.append("HTTP status changed")
        if response_size_changed:
            reasons.append(f"Response size changed from {baseline_size} to {candidate_size} bytes")
        if data_leakage_detected:
            reasons.append(f"New leakage patterns: {', '.join(new_leaks)}")

        severity = {
            "Confirmed": "high",
            "Inconclusive": "informational",
            "Not Confirmed": "low",
        }[decision]

        return {
            "mutation_name": mutation.get("name"),
            "hypothesis_name": (hypothesis or {}).get("name"),
            "decision": decision,
            "is_interesting": decision == "Confirmed",
            "severity": severity,
            "status_changed": status_changed,
            "body_changed": body_changed,
            "response_size_changed": response_size_changed,
            "data_leakage_detected": data_leakage_detected,
            "new_leakage_patterns": new_leaks,
            "baseline_status": baseline.get("status_code"),
            "candidate_status": candidate.get("status_code"),
            "baseline_size": baseline_size,
            "candidate_size": candidate_size,
            "reasons": reasons,
        }

    def _canonicalize(self, body: Any) -> str:
        if isinstance(body, (dict, list)):
            return json.dumps(body, sort_keys=True, ensure_ascii=True)
        return str(body)

    def _detect_leakage(self, body_text: str) -> set[str]:
        matches: set[str] = set()
        for pattern in self.LEAKAGE_PATTERNS:
            if pattern.search(body_text):
                matches.add(pattern.pattern)
        return matches
