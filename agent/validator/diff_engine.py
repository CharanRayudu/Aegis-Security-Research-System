"""Response diffing and finding detection for IDOR validation."""

from __future__ import annotations

import json
from typing import Any


class DiffEngine:
    """Compares baseline and mutated responses for IDOR-specific signals."""

    IDENTITY_KEYS = {"id", "user_id", "owner_id", "account_id"}
    IGNORED_KEYS = {"created_at", "updated_at", "timestamp", "last_updated"}

    def compare(
        self,
        baseline: dict[str, Any],
        candidate: dict[str, Any],
        mutation: dict[str, Any],
        hypothesis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        baseline_status = baseline.get("status_code", 0)
        candidate_status = candidate.get("status_code", 0)
        baseline_success = 200 <= baseline_status < 300
        candidate_success = 200 <= candidate_status < 300

        baseline_body = baseline.get("body")
        candidate_body = candidate.get("body")
        baseline_text = self._canonicalize(baseline_body)
        candidate_text = self._canonicalize(candidate_body)
        baseline_size = len(baseline_text)
        candidate_size = len(candidate_text)
        status_changed = baseline_status != candidate_status
        body_changed = baseline_text != candidate_text
        response_size_changed = abs(candidate_size - baseline_size) >= 40

        evidence: list[str] = []
        key_differences: list[str] = []
        identity_changes: list[str] = []
        ownership_changes: list[str] = []
        clearly_different_object = False
        json_compared = False

        if baseline_status == 0 or candidate_status == 0:
            decision = "Inconclusive"
            confidence = "low"
            evidence.append("Transport failure prevented a reliable authorization comparison")
            reason = "The validator could not compare access-control behavior because at least one request failed before an HTTP response was received."
        else:
            baseline_json = self._to_json_like(baseline_body)
            candidate_json = self._to_json_like(candidate_body)

            if baseline_json is not None and candidate_json is not None:
                json_compared = True
                json_diff = self.compare_json(baseline_json, candidate_json)
                key_differences = json_diff["key_differences"]
                identity_changes = json_diff["identity_changes"]
                ownership_changes = json_diff["ownership_changes"]
                clearly_different_object = json_diff["clearly_different_object"]
                evidence.extend(json_diff["evidence"])

            if baseline_success and candidate_status in {401, 403}:
                decision = "Not Confirmed"
                confidence = "high"
                evidence.append(f"Mutated request was denied with {candidate_status}")
                reason = "The mutated identifier did not preserve successful access. The target appears to enforce authorization for the modified object."
            elif baseline_success and candidate_success:
                if identity_changes or ownership_changes or clearly_different_object:
                    decision = "Confirmed"
                    confidence = "high"
                    evidence.append("Response remained successful after identifier mutation")
                    reason = "The mutated request stayed successful and returned evidence of a different object identity or ownership context."
                elif json_compared:
                    decision = "Inconclusive"
                    confidence = "medium" if (response_size_changed or key_differences) else "low"
                    if response_size_changed:
                        evidence.append(f"Response size changed from {baseline_size} to {candidate_size} bytes")
                    if key_differences:
                        evidence.append(f"JSON key differences detected: {', '.join(key_differences[:5])}")
                    reason = "The response changed, but the validator could not prove that a different unauthorized object was returned."
                elif body_changed or response_size_changed:
                    decision = "Inconclusive"
                    confidence = "low"
                    if response_size_changed:
                        evidence.append(f"Response size changed from {baseline_size} to {candidate_size} bytes")
                    reason = "Only text-level or size-level differences were observed. That is not strong enough to confirm IDOR."
                else:
                    decision = "Not Confirmed"
                    confidence = "medium"
                    reason = "The mutated identifier produced the same successful response shape with no evidence of a different object."
            elif baseline_success and candidate_status in {404}:
                decision = "Not Confirmed"
                confidence = "medium"
                evidence.append("Mutated request did not return another object")
                reason = "The modified identifier did not produce a successful object fetch."
            elif baseline_status in {401, 403, 404} and candidate_success:
                if identity_changes or ownership_changes or clearly_different_object:
                    decision = "Confirmed"
                    confidence = "high"
                    evidence.append("Mutated identifier returned a successful object response while baseline did not")
                    reason = "The mutated request gained access and the response indicates a different object or ownership context."
                else:
                    decision = "Inconclusive"
                    confidence = "medium"
                    evidence.append("Mutated identifier returned success while baseline did not")
                    reason = "Authorization behavior changed, but the validator lacks object-level evidence proving unauthorized access to a different record."
            else:
                if not json_compared and body_changed:
                    decision = "Inconclusive"
                    confidence = "low"
                    reason = "JSON parsing was not available for both responses, so only weak text-level evidence exists."
                else:
                    decision = "Not Confirmed"
                    confidence = "low"
                    reason = "No strong IDOR evidence was found."

        if status_changed:
            evidence.append(f"HTTP status changed from {baseline_status} to {candidate_status}")

        severity = {
            "Confirmed": "high",
            "Inconclusive": "informational",
            "Not Confirmed": "low",
        }[decision]

        return {
            "mutation_name": mutation.get("name"),
            "hypothesis_name": (hypothesis or {}).get("name"),
            "decision": decision,
            "confidence": confidence,
            "evidence": evidence,
            "reason": reason,
            "is_interesting": decision == "Confirmed",
            "severity": severity,
            "status_changed": status_changed,
            "body_changed": body_changed,
            "response_size_changed": response_size_changed,
            "baseline_status": baseline_status,
            "candidate_status": candidate_status,
            "baseline_size": baseline_size,
            "candidate_size": candidate_size,
            "identity_changes": identity_changes,
            "ownership_changes": ownership_changes,
            "key_differences": key_differences,
            "json_compared": json_compared,
            "reasons": evidence or [reason],
        }

    def compare_json(self, baseline_json: Any, mutated_json: Any) -> dict[str, Any]:
        """Return structured JSON differences relevant to IDOR detection."""

        evidence: list[str] = []
        key_differences: list[str] = []
        identity_changes: list[str] = []
        ownership_changes: list[str] = []
        clearly_different_object = False

        baseline_paths = self._collect_json_paths(baseline_json)
        mutated_paths = self._collect_json_paths(mutated_json)

        baseline_keys = set(baseline_paths.keys())
        mutated_keys = set(mutated_paths.keys())
        added = sorted(mutated_keys - baseline_keys)
        removed = sorted(baseline_keys - mutated_keys)
        if added:
            key_differences.extend(f"+{path}" for path in added[:10])
        if removed:
            key_differences.extend(f"-{path}" for path in removed[:10])

        shared_paths = sorted(baseline_keys & mutated_keys)
        for path in shared_paths:
            if self._ignored_path(path):
                continue

            baseline_value = baseline_paths[path]
            mutated_value = mutated_paths[path]
            if baseline_value == mutated_value:
                continue

            leaf_key = path.split(".")[-1]
            if leaf_key in self.IDENTITY_KEYS:
                identity_changes.append(f"{path}: {baseline_value} -> {mutated_value}")
                evidence.append(f"Object ID changed from {baseline_value} to {mutated_value} at {path}")
                clearly_different_object = True
            elif "owner" in leaf_key:
                ownership_changes.append(f"{path}: {baseline_value} -> {mutated_value}")
                evidence.append(f"Ownership indicator changed from {baseline_value} to {mutated_value} at {path}")
                clearly_different_object = True
            elif self._is_person_like_field(leaf_key) and baseline_value != mutated_value:
                evidence.append(f"Field {path} changed from {baseline_value} to {mutated_value}")

        baseline_root_id = self._extract_identity_snapshot(baseline_json)
        mutated_root_id = self._extract_identity_snapshot(mutated_json)
        if baseline_root_id and mutated_root_id and baseline_root_id != mutated_root_id:
            clearly_different_object = True
            evidence.append(
                f"Different object identity detected: baseline {baseline_root_id} vs mutated {mutated_root_id}"
            )

        return {
            "key_differences": key_differences,
            "identity_changes": identity_changes,
            "ownership_changes": ownership_changes,
            "clearly_different_object": clearly_different_object,
            "evidence": evidence,
        }

    def _to_json_like(self, body: Any) -> Any | None:
        if isinstance(body, (dict, list)):
            return body
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
            except (TypeError, ValueError, json.JSONDecodeError):
                return None
            if isinstance(parsed, (dict, list)):
                return parsed
        return None

    def _collect_json_paths(self, value: Any, prefix: str = "") -> dict[str, Any]:
        paths: dict[str, Any] = {}
        if isinstance(value, dict):
            for key, nested in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                paths.update(self._collect_json_paths(nested, path))
        elif isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                for item in value[:3]:
                    paths.update(self._collect_json_paths(item, prefix))
            else:
                paths[prefix or "root"] = value
        else:
            paths[prefix or "root"] = value
        return paths

    def _extract_identity_snapshot(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            snapshot = {key: val for key, val in value.items() if key in self.IDENTITY_KEYS or "owner" in key}
            if snapshot:
                return snapshot
            for nested in value.values():
                nested_snapshot = self._extract_identity_snapshot(nested)
                if nested_snapshot:
                    return nested_snapshot
        elif isinstance(value, list):
            for item in value[:3]:
                nested_snapshot = self._extract_identity_snapshot(item)
                if nested_snapshot:
                    return nested_snapshot
        return {}

    def _ignored_path(self, path: str) -> bool:
        leaf_key = path.split(".")[-1]
        return leaf_key in self.IGNORED_KEYS

    def _is_person_like_field(self, key: str) -> bool:
        lowered = key.lower()
        return lowered in {"username", "email", "name", "full_name"}

    def _canonicalize(self, body: Any) -> str:
        if isinstance(body, (dict, list)):
            return json.dumps(body, sort_keys=True, ensure_ascii=True)
        return str(body)
