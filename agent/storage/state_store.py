"""Persistent state tracking for autonomous runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StateStore:
    """Stores known and tested endpoints to avoid duplicate work."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.state_path = self.base_dir / "raw" / "agent_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._write(
                {
                    "tested_endpoints": {},
                    "known_endpoints": [],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    def _read(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write(self, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def is_endpoint_tested(self, signature: str) -> bool:
        state = self._read()
        return signature in state["tested_endpoints"]

    def mark_endpoint_tested(self, signature: str, metadata: dict[str, Any]) -> None:
        state = self._read()
        state["tested_endpoints"][signature] = metadata
        self._write(state)
        print(f"[state] Marked tested endpoint {signature}")

    def add_known_endpoint(self, endpoint: dict[str, Any]) -> None:
        state = self._read()
        signature = f"{endpoint.get('method', 'GET').upper()}::{endpoint['path']}"
        signatures = {
            f"{item.get('method', 'GET').upper()}::{item['path']}"
            for item in state["known_endpoints"]
        }
        if signature in signatures:
            return
        state["known_endpoints"].append(endpoint)
        self._write(state)
        print(f"[state] Stored known endpoint {signature}")
