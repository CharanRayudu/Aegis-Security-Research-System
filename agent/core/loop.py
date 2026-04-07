"""Main autonomous security research loop."""

from __future__ import annotations

from pathlib import Path
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

import yaml

from agent.core.discovery import EndpointDiscovery
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
    """Coordinates endpoint collection, hypothesis generation, execution, discovery, and storage."""

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.base_dir = Path(config_path).resolve().parent
        self.config = self._load_config(config_path)
        self.writer = MarkdownWriter(base_dir=str(self.base_dir))
        self.state_store = StateStore(base_dir=str(self.base_dir))
        self.memory_store = MemoryStore(base_dir=str(self.base_dir))
        self.discovery = EndpointDiscovery(base_url=self.config["base_url"])
        self.mutation_engine = MutationEngine()
        self.diff_engine = DiffEngine()
        self.executor = self._build_executor()

    def _build_executor(self) -> HttpExecutor:
        return HttpExecutor(
            base_url=self.config["base_url"],
            default_headers=self.config.get("headers", {}),
            auth=self.config.get("auth") or {},
        )

    def _load_config(self, config_path: str) -> dict[str, Any]:
        print(f"[loop] Loading config from {config_path}")
        with open(config_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _reload_runtime(self) -> None:
        self.config = self._load_config(self.config_path)
        self.executor = self._build_executor()

    def _load_endpoints(self) -> list[EndpointRecord]:
        endpoint_rows = self.config.get("endpoints", [])
        print(f"[loop] Loaded {len(endpoint_rows)} endpoint(s) from config")
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
        for endpoint in endpoints:
            self.state_store.add_known_endpoint(asdict(endpoint))
        return endpoints

    def _enqueue_untested(self, queue: deque[EndpointRecord], enqueued: set[str]) -> int:
        count = 0
        for endpoint in self._load_endpoints():
            signature = endpoint.signature()
            if signature in enqueued or self.state_store.is_endpoint_tested(signature):
                continue
            queue.append(endpoint)
            enqueued.add(signature)
            count += 1
        return count

    def _persist_endpoint_catalog(self, endpoint: EndpointRecord) -> None:
        catalog = self.config.setdefault("endpoints", [])
        candidate = {
            "path": endpoint.path,
            "method": endpoint.method.upper(),
            "params": endpoint.params or {},
            "headers": endpoint.headers or {},
            "body": endpoint.body or {},
            "source": endpoint.source,
        }
        if any(
            row.get("path") == candidate["path"] and row.get("method", "GET").upper() == candidate["method"]
            for row in catalog
        ):
            return

        catalog.append(candidate)
        with open(self.config_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(self.config, handle, sort_keys=False)
        print(f"[loop] Persisted discovered endpoint {candidate['method']} {candidate['path']} to config")

    def _register_discovered_endpoints(
        self,
        queue: deque[EndpointRecord],
        enqueued: set[str],
        discovered: list[dict[str, Any]],
    ) -> int:
        added = 0
        for entry in discovered:
            endpoint = EndpointRecord(
                path=entry["path"],
                method=entry.get("method", "GET"),
                params=entry.get("params") or {},
                headers=entry.get("headers") or {},
                body=entry.get("body") or {},
                source=entry.get("source", "discovered"),
            )
            signature = endpoint.signature()
            if signature in enqueued or self.state_store.is_endpoint_tested(signature):
                continue

            self._persist_endpoint_catalog(endpoint)
            self.state_store.add_known_endpoint(asdict(endpoint))
            self.writer.write_endpoint(asdict(endpoint))
            queue.append(endpoint)
            enqueued.add(signature)
            added += 1
            print(f"[loop] Discovered new endpoint {signature}")
        return added

    def _build_endpoint_payload(self, endpoint: EndpointRecord) -> dict[str, Any]:
        return {
            "base_url": self.config["base_url"],
            "path": endpoint.path,
            "method": endpoint.method.upper(),
            "params": endpoint.params or {},
            "headers": endpoint.headers or {},
            "body": endpoint.body or {},
            "source": endpoint.source,
        }

    def _run_endpoint(self, endpoint: EndpointRecord) -> dict[str, Any]:
        endpoint_payload = self._build_endpoint_payload(endpoint)
        signature = endpoint.signature()
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

        memory_query = f"{endpoint.method.upper()} {endpoint.path}"
        memory_context = self.memory_store.search_memory(memory_query)
        print(f"[loop] Using {len(memory_context)} memory item(s) to inform hypotheses for {signature}")
        hypotheses = generate_hypotheses(endpoint_payload, memory_context=memory_context)
        top_hypothesis = hypotheses[0]
        hypothesis_record = {
            "endpoint": endpoint_payload,
            "selected_hypothesis": top_hypothesis,
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

        discovered = self.discovery.discover_from_response(baseline)
        experiments: list[dict[str, Any]] = []

        for index, hypothesis in enumerate(hypotheses, start=1):
            print(
                f"[loop] Hypothesis {index}/{len(hypotheses)} "
                f"confidence={hypothesis['confidence']:.2f} {hypothesis['name']}"
            )
            mutations = self.mutation_engine.generate_mutations(
                endpoint=endpoint_payload,
                hypothesis=hypothesis,
            )
            for mutation_index, mutation in enumerate(mutations, start=1):
                print(
                    f"[loop] Mutation {mutation_index}/{len(mutations)} for {signature}: "
                    f"{mutation['name']}"
                )
                experiment_response = self.executor.send_request(
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
                    candidate=experiment_response,
                    mutation=mutation,
                    hypothesis=hypothesis,
                )
                discovered.extend(self.discovery.discover_from_response(experiment_response))

                experiment_record = {
                    "endpoint": endpoint_payload,
                    "hypothesis": hypothesis,
                    "mutation": mutation,
                    "baseline": baseline,
                    "candidate": experiment_response,
                    "validation": validation,
                }
                self.writer.write_experiment(endpoint.path, mutation["name"], experiment_record)
                self.writer.write_finding(endpoint.path, mutation["name"], experiment_record)
                self.memory_store.save_memory(
                    {
                        "type": "experiment",
                        "label": f"{signature}::{mutation['name']}",
                        "path": endpoint.path,
                        "method": endpoint.method.upper(),
                        "mutation_name": mutation["name"],
                        "payload": experiment_record,
                    }
                )
                if validation["is_interesting"]:
                    self.memory_store.save_memory(
                        {
                            "type": "finding",
                            "label": f"{signature}::{mutation['name']}",
                            "path": endpoint.path,
                            "method": endpoint.method.upper(),
                            "severity": validation["severity"],
                            "payload": experiment_record,
                        }
                    )
                experiments.append(experiment_record)

        self.state_store.mark_endpoint_tested(
            signature,
            {
                "path": endpoint.path,
                "method": endpoint.method.upper(),
                "last_run_status": baseline.get("status_code"),
                "source": endpoint.source,
            },
        )
        return {
            "endpoint": endpoint_payload,
            "selected_hypothesis": top_hypothesis,
            "hypotheses": hypotheses,
            "baseline": baseline,
            "experiments": experiments,
            "discovered_endpoints": discovered,
        }

    def run_cycle(self) -> list[dict[str, Any]]:
        self._reload_runtime()
        queue: deque[EndpointRecord] = deque()
        enqueued: set[str] = set()
        seeded = self._enqueue_untested(queue, enqueued)
        print(f"[loop] Seeded queue with {seeded} untested endpoint(s)")

        results: list[dict[str, Any]] = []
        while queue:
            endpoint = queue.popleft()
            result = self._run_endpoint(endpoint)
            results.append(result)
            new_count = self._register_discovered_endpoints(
                queue=queue,
                enqueued=enqueued,
                discovered=result["discovered_endpoints"],
            )
            print(
                f"[loop] Completed {endpoint.signature()} | experiments={len(result['experiments'])} "
                f"| new_endpoints={new_count} | queue_remaining={len(queue)}"
            )

        print(f"[loop] Cycle complete with {len(results)} processed endpoint(s)")
        return results

    def run(self) -> list[dict[str, Any]]:
        return self.run_cycle()

    def run_forever(self) -> None:
        cycle = 0
        print("[loop] Continuous mode enabled")
        while True:
            cycle += 1
            print(f"[loop] === Cycle {cycle} start ===")
            results = self.run_cycle()
            print(f"[loop] === Cycle {cycle} end | processed={len(results)} ===")
            loop_interval = int(self.config.get("loop_interval_seconds", 30))
            print(f"[loop] Sleeping for {loop_interval}s before next cycle")
            time.sleep(loop_interval)
