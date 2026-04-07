"""Main IDOR-focused research loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from agent.executor.http_client import HttpExecutor
from agent.executor.mutation_engine import MutationEngine
from agent.llm.reasoner import generate_hypotheses
from agent.memory.store import MemoryStore
from agent.storage.markdown_writer import MarkdownWriter
from agent.storage.state_store import StateStore
from agent.validator.diff_engine import DiffEngine


@dataclass
class EndpointRecord:
    path: str
    method: str = "GET"
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    body: dict[str, Any] | None = None
    source: str = "config"

    def signature(self) -> str:
        return f"{self.method.upper()}::{self.path}"


class AutonomousResearchLoop:
    """Runs one local IDOR research pass across configured endpoints."""

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.base_dir = Path(config_path).resolve().parent
        self.config = self._load_config(config_path)
        self.writer = MarkdownWriter(base_dir=str(self.base_dir))
        self.state_store = StateStore(base_dir=str(self.base_dir))
        self.memory_store = MemoryStore(base_dir=str(self.base_dir))
        self.mutation_engine = MutationEngine()
        self.diff_engine = DiffEngine()
        self.executor = HttpExecutor(
            base_url=self.config["base_url"],
            default_headers=self.config.get("headers", {}),
            auth=self.config.get("auth") or {},
        )

    def _load_config(self, config_path: str) -> dict[str, Any]:
        print(f"[loop] Loading config from {config_path}")
        with open(config_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _load_endpoints(self) -> list[EndpointRecord]:
        endpoint_rows = self.config.get("endpoints", [])
        endpoints = [
            EndpointRecord(
                path=row["path"],
                method=row.get("method", "GET"),
                params=row.get("params") or {},
                headers=row.get("headers") or {},
                body=row.get("body") or {},
                source=row.get("source", "config"),
            )
            for row in endpoint_rows
        ]
        print(f"[loop] Loaded {len(endpoints)} endpoint(s) from config")
        for endpoint in endpoints:
            self.state_store.add_known_endpoint(asdict(endpoint))
        return endpoints

    def _resource_from_path(self, path: str) -> str:
        segments = [segment for segment in path.split("/") if segment]
        for segment in reversed(segments):
            lowered = segment.lower()
            if segment.isdigit() or lowered in {"api", "rest", "v1", "v2", "v3"}:
                continue
            return segment
        return "resource"

    def _endpoint_payload(self, endpoint: EndpointRecord) -> dict[str, Any]:
        return {
            "base_url": self.config["base_url"],
            "path": endpoint.path,
            "method": endpoint.method.upper(),
            "params": endpoint.params or {},
            "headers": endpoint.headers or {},
            "body": endpoint.body or {},
            "source": endpoint.source,
            "resource": self._resource_from_path(endpoint.path),
        }

    def run(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        endpoints = self._load_endpoints()
        confirmed_findings = 0
        print("[loop] Starting single-pass IDOR research run")

        for endpoint in endpoints:
            signature = endpoint.signature()
            endpoint_payload = self._endpoint_payload(endpoint)
            print(f"[loop] Processing {signature}")
            self.writer.write_endpoint(endpoint_payload)
            self.memory_store.save_memory(
                {
                    "type": "endpoint",
                    "label": signature,
                    "path": endpoint.path,
                    "method": endpoint.method.upper(),
                    "payload": endpoint_payload,
                }
            )

            memory_context = self.memory_store.search_memory(f"{endpoint.method.upper()} {endpoint_payload['resource']}")
            hypotheses = generate_hypotheses(endpoint_payload, memory_context=memory_context)
            if not hypotheses:
                print(f"[loop] No hypotheses generated for {signature}, skipping endpoint")
                continue
            hypothesis_record = {
                "endpoint": endpoint_payload,
                "selected_hypothesis": hypotheses[0],
                "hypotheses": hypotheses,
                "memory_context": memory_context,
            }
            self.writer.write_hypothesis(endpoint.path, hypothesis_record)
            self.memory_store.save_memory(
                {
                    "type": "hypothesis",
                    "label": signature,
                    "path": endpoint.path,
                    "method": endpoint.method.upper(),
                    "payload": hypothesis_record,
                }
            )

            baseline = self.executor.send_request(
                path=endpoint.path,
                method=endpoint.method,
                params=endpoint.params,
                extra_headers=endpoint.headers,
                json_body=endpoint.body,
            )

            experiments: list[dict[str, Any]] = []
            executed_mutations: set[str] = set()
            for hypothesis in hypotheses:
                mutations = self.mutation_engine.generate_mutations(endpoint_payload, hypothesis)
                print(f"[loop] Evaluating {len(mutations)} candidate mutation(s) for hypothesis {hypothesis['name']}")
                for mutation in mutations:
                    mutation_signature = (
                        mutation.get("path", endpoint.path),
                        str(sorted((mutation.get("params") or {}).items())),
                    )
                    if str(mutation_signature) in executed_mutations:
                        continue
                    executed_mutations.add(str(mutation_signature))

                    candidate = self.executor.send_request(
                        path=mutation.get("path", endpoint.path),
                        method=endpoint.method,
                        params=mutation.get("params", endpoint.params),
                        extra_headers={
                            **(endpoint.headers or {}),
                            **mutation.get("headers", {}),
                        },
                        json_body=mutation.get("body", endpoint.body),
                    )
                    validation = self.diff_engine.compare(
                        baseline=baseline,
                        candidate=candidate,
                        mutation=mutation,
                        hypothesis=hypothesis,
                    )
                    experiment_record = {
                        "endpoint": endpoint_payload,
                        "hypothesis": hypothesis,
                        "mutation": mutation,
                        "baseline": baseline,
                        "candidate": candidate,
                        "validation": validation,
                    }
                    self.writer.write_experiment(endpoint.path, mutation["name"], experiment_record)
                    self.memory_store.save_memory(
                        {
                            "type": "experiment",
                            "label": f"{signature}::{mutation['name']}",
                            "path": endpoint.path,
                            "method": endpoint.method.upper(),
                            "payload": experiment_record,
                        }
                    )
                    if validation["decision"] == "Confirmed":
                        self.writer.write_finding(endpoint.path, mutation["name"], experiment_record)
                        self.memory_store.save_memory(
                            {
                                "type": "finding",
                                "label": f"{signature}::{mutation['name']}",
                                "path": endpoint.path,
                                "method": endpoint.method.upper(),
                                "payload": experiment_record,
                            }
                        )
                        confirmed_findings += 1
                    experiments.append(experiment_record)

            self.state_store.mark_endpoint_tested(
                signature,
                {
                    "path": endpoint.path,
                    "method": endpoint.method.upper(),
                    "source": endpoint.source,
                    "baseline_status": baseline.get("status_code"),
                    "experiment_count": len(experiments),
                },
            )
            results.append(
                {
                    "endpoint": endpoint_payload,
                    "baseline": baseline,
                    "hypotheses": hypotheses,
                    "experiments": experiments,
                }
            )
            print(f"[loop] Completed {signature} with {len(experiments)} experiment(s)")

        self.writer.rebuild_findings_index()
        print(f"[loop] Rebuilt findings index with {confirmed_findings} confirmed finding(s)")
        print(f"[loop] Run complete. Processed {len(results)} endpoint(s)")
        return results
