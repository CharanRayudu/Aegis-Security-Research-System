"""Persistent state tracking for autonomous runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any


class StateStore:
    """Stores known and tested endpoints to avoid duplicate work."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.state_path = self.base_dir / "raw" / "agent_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._write(self._default_state())

    def _read(self) -> dict[str, Any]:
        if not self.state_path.exists():
            state = self._default_state()
            self._write(state)
            return state

        try:
            raw_text = self.state_path.read_text(encoding="utf-8-sig")
            if not raw_text.strip():
                raise JSONDecodeError("empty file", raw_text, 0)
            state = json.loads(raw_text)
        except (OSError, JSONDecodeError, ValueError):
            state = self._default_state()
            self._write(state)
            print(f"[state] Recreated invalid or empty state file at {self.state_path}")
            return state

        if not isinstance(state, dict):
            state = self._default_state()
            self._write(state)
            print(f"[state] Recreated malformed state structure at {self.state_path}")
            return state

        state.setdefault("tested_endpoints", {})
        state.setdefault("known_endpoints", [])
        return state

    def _write(self, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def _default_state(self) -> dict[str, Any]:
        return {
            "tested_endpoints": {},
            "known_endpoints": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

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
