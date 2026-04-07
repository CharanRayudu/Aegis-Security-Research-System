"""Local JSON-backed memory store for autonomous research."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryStore:
    """Persists and searches historical research context locally."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.memory_path = self.base_dir / "raw" / "memory_store.json"
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self._write(
                {
                    "entries": [],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    def _read(self) -> dict[str, Any]:
        return json.loads(self.memory_path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def save_memory(self, data: dict[str, Any]) -> dict[str, Any]:
        memory = self._read()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        memory["entries"].append(entry)
        self._write(memory)
        print(f"[memory] Saved {entry.get('type', 'unknown')} memory entry")
        return entry

    def search_memory(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, dict[str, Any]]] = []
        for entry in self._read()["entries"]:
            searchable = json.dumps(entry, sort_keys=True).lower()
            score = sum(1 for token in query_tokens if token in searchable)
            if score:
                scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]
        print(f"[memory] Search query='{query}' returned {len(results)} result(s)")
        return results

    def _tokenize(self, query: str) -> list[str]:
        return [token.strip().lower() for token in query.split() if token.strip()]
