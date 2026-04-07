"""Markdown output writer for the Obsidian vault."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MarkdownWriter:
    """Writes Obsidian-compatible markdown notes for research artifacts."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.output_dirs = {
            "endpoints": self.base_dir / "endpoints",
            "resources": self.base_dir / "resources",
            "hypotheses": self.base_dir / "hypotheses",
            "experiments": self.base_dir / "experiments",
            "findings": self.base_dir / "findings",
        }
        self.index_path = self.base_dir / "index.md"
        for directory in self.output_dirs.values():
            directory.mkdir(parents=True, exist_ok=True)

    def write_endpoint(self, endpoint_payload: dict[str, Any]) -> str:
        slug = self._slugify(endpoint_payload["path"])
        resource_slug = self._resource_slug(endpoint_payload["path"])
        self.write_resource(endpoint_payload["path"], endpoint_payload)
        path = self.output_dirs["endpoints"] / f"{slug}.md"
        links = [
            self._wikilink("resources", resource_slug),
            self._wikilink("hypotheses", slug),
        ]
        content = self._build_note(
            title=f"Endpoint: {endpoint_payload.get('method', 'GET')} {endpoint_payload['path']}",
            summary_lines=[
                f"Generated: {self._timestamp()}",
                f"Method: `{endpoint_payload.get('method', 'GET')}`",
                f"Path: `{endpoint_payload['path']}`",
                f"Resource: {self._wikilink('resources', resource_slug)}",
            ],
            links=links,
            payload=endpoint_payload,
        )
        path.write_text(content, encoding="utf-8")
        print(f"[storage] Wrote endpoint markdown to {path}")
        return str(path)

    def write_resource(self, endpoint_path: str, payload: dict[str, Any]) -> str:
        resource_slug = self._resource_slug(endpoint_path)
        path = self.output_dirs["resources"] / f"{resource_slug}.md"
        endpoint_slug = self._slugify(endpoint_path)
        content = self._build_note(
            title=f"Resource: {resource_slug}",
            summary_lines=[
                f"Generated: {self._timestamp()}",
                f"Resource Key: `{resource_slug}`",
                f"Observed Via: `{endpoint_path}`",
            ],
            links=[
                self._wikilink("endpoints", endpoint_slug),
                self._wikilink("index"),
            ],
            payload=payload,
        )
        path.write_text(content, encoding="utf-8")
        print(f"[storage] Wrote resource markdown to {path}")
        return str(path)

    def write_hypothesis(self, endpoint_path: str, hypothesis: dict[str, Any]) -> str:
        slug = self._slugify(endpoint_path)
        resource_slug = self._resource_slug(endpoint_path)
        self.write_resource(endpoint_path, hypothesis.get("endpoint", {"path": endpoint_path}))
        path = self.output_dirs["hypotheses"] / f"{slug}.md"
        selected = hypothesis.get("selected_hypothesis", {})
        content = self._build_note(
            title=f"Hypothesis: {endpoint_path}",
            summary_lines=[
                f"Generated: {self._timestamp()}",
                f"Top Hypothesis: `{selected.get('name', 'unknown')}`",
                f"Confidence: `{selected.get('confidence', 'n/a')}`",
                f"Resource: {self._wikilink('resources', resource_slug)}",
            ],
            links=[
                self._wikilink("resources", resource_slug),
                self._wikilink("endpoints", slug),
            ],
            payload=hypothesis,
        )
        path.write_text(content, encoding="utf-8")
        print(f"[storage] Wrote hypothesis markdown to {path}")
        return str(path)

    def write_experiment(self, endpoint_path: str, mutation_name: str, experiment: dict[str, Any]) -> str:
        slug = self._slugify(f"{endpoint_path}_{mutation_name}")
        endpoint_slug = self._slugify(endpoint_path)
        resource_slug = self._resource_slug(endpoint_path)
        self.write_resource(endpoint_path, experiment.get("endpoint", {"path": endpoint_path}))
        path = self.output_dirs["experiments"] / f"{slug}.md"
        content = self._build_note(
            title=f"Experiment: {mutation_name}",
            summary_lines=[
                f"Generated: {self._timestamp()}",
                f"Endpoint: {self._wikilink('endpoints', endpoint_slug)}",
                f"Mutation: `{mutation_name}`",
                f"Resource: {self._wikilink('resources', resource_slug)}",
            ],
            links=[
                self._wikilink("resources", resource_slug),
                self._wikilink("endpoints", endpoint_slug),
                self._wikilink("hypotheses", endpoint_slug),
            ],
            payload=experiment,
        )
        path.write_text(content, encoding="utf-8")
        print(f"[storage] Wrote experiment markdown to {path}")
        return str(path)

    def write_finding(self, endpoint_path: str, mutation_name: str, finding: dict[str, Any]) -> str:
        slug = self._slugify(f"{endpoint_path}_{mutation_name}")
        endpoint_slug = self._slugify(endpoint_path)
        resource_slug = self._resource_slug(endpoint_path)
        self.write_resource(endpoint_path, finding.get("endpoint", {"path": endpoint_path}))
        path = self.output_dirs["findings"] / f"{slug}.md"
        validation = finding.get("validation", {})
        content = self._build_note(
            title=f"Finding: {mutation_name}",
            summary_lines=[
                f"Generated: {self._timestamp()}",
                f"Severity: `{validation.get('severity', 'informational')}`",
                f"Endpoint: {self._wikilink('endpoints', endpoint_slug)}",
                f"Resource: {self._wikilink('resources', resource_slug)}",
            ],
            links=[
                self._wikilink("resources", resource_slug),
                self._wikilink("endpoints", endpoint_slug),
                self._wikilink("hypotheses", endpoint_slug),
                self._wikilink("experiments", slug),
                self._wikilink("index"),
            ],
            payload=finding,
        )
        path.write_text(content, encoding="utf-8")
        print(f"[storage] Wrote finding markdown to {path}")
        return str(path)

    def rebuild_findings_index(self) -> None:
        finding_links = sorted(
            self._wikilink("findings", item.stem)
            for item in self.output_dirs["findings"].glob("*.md")
        )
        if not finding_links:
            finding_lines = ["- No findings recorded yet."]
        else:
            finding_lines = [f"- {link}" for link in finding_links]

        content = (
            "# Findings Index\n\n"
            "## Summary\n"
            f"- Generated: {self._timestamp()}\n"
            f"- Total Findings: `{len(list(self.output_dirs['findings'].glob('*.md')))}`\n\n"
            "## Findings\n"
            + "\n".join(finding_lines)
            + "\n"
        )
        self.index_path.write_text(content, encoding="utf-8")
        print(f"[storage] Updated findings index at {self.index_path}")

    def _build_note(
        self,
        title: str,
        summary_lines: list[str],
        links: list[str],
        payload: dict[str, Any],
    ) -> str:
        pretty_json = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        summary = "\n".join(f"- {line}" for line in summary_lines)
        related = "\n".join(f"- {link}" for link in links)
        return (
            f"# {title}\n\n"
            "## Summary\n"
            f"{summary}\n\n"
            "## Links\n"
            f"{related}\n\n"
            "## Details\n"
            "```json\n"
            f"{pretty_json}\n"
            "```\n"
        )

    def _resource_slug(self, endpoint_path: str) -> str:
        clean_path = endpoint_path.split("?", 1)[0].strip("/")
        segments = [segment for segment in clean_path.split("/") if segment]
        for segment in reversed(segments):
            lowered = segment.lower()
            if segment.isdigit() or lowered in {"api", "rest", "v1", "v2", "v3"}:
                continue
            return self._slugify(segment)
        return "resource"

    def _wikilink(self, folder: str, slug: str | None = None) -> str:
        if slug is None:
            return f"[[{folder}]]"
        return f"[[{folder}/{slug}]]"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _slugify(self, value: str) -> str:
        cleaned = value.strip().replace("\\", "/").replace("/", "_")
        allowed = [char if char.isalnum() or char in {"_", "-", "."} else "_" for char in cleaned]
        slug = "".join(allowed).strip("._")
        return slug or f"record_{os.getpid()}"
