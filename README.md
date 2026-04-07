# Aegis Security Research System

`Aegis-Security-Research-System` is an early-stage deterministic, local-first Security Research Intelligence System built for narrow HTTP authorization research.

This repository is not a fully autonomous pentesting system. The current v1 is intentionally narrow: it performs deterministic IDOR-style HTTP testing against endpoints defined in configuration, compares baseline and mutated responses, and stores the results in an Obsidian-compatible vault layout.

## Current v1 Scope

The current implementation supports:

- deterministic HTTP request execution
- baseline versus mutated request comparison
- IDOR and broken object-level authorization style testing only
- JSON or text response comparison
- local markdown note generation
- local JSON memory and state tracking

The current implementation does not support:

- browser instrumentation
- generalized vulnerability scanning
- XSS, SQLi, SSRF, RCE, or workflow automation
- continuous autonomous operation
- scheduling
- distributed workers
- a true agent swarm

## How v1 Works

For each endpoint in `config.yaml`, the system:

1. loads the configured base URL and endpoint metadata
2. sends a baseline HTTP request
3. generates a small IDOR-focused hypothesis set
4. mutates path or query identifiers
5. sends the modified requests
6. compares the responses
7. classifies each result as `Confirmed`, `Not Confirmed`, or `Inconclusive`
8. writes markdown notes into the vault folders
9. stores local memory and state in `raw/`

## Repository Structure

```text
Aegis-Security-Research-System/
|- agent/
|  |- core/
|  |  `- loop.py
|  |- executor/
|  |  `- http_client.py
|  |- llm/
|  |  `- reasoner.py
|  |- memory/
|  |  `- store.py
|  |- storage/
|  |  `- markdown_writer.py
|  `- validator/
|     `- diff_engine.py
|- scripts/
|  `- run_agent.py
|- raw/
|- endpoints/
|- resources/
|- auth/
|- workflows/
|- hypotheses/
|- experiments/
|- findings/
|- notes/
|  `- prompts.md
|- config.yaml
|- requirements.txt
|- .gitignore
`- index.md
```

## Setup

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

The default v1 path is deterministic and local-first. No OpenAI package or API key is required for the core workflow.

## Configuration

Edit `config.yaml` before running:

```yaml
base_url: "https://example.com"
headers:
  Accept: "application/json"
  User-Agent: "Aegis-Security-Research-System/1.0"
auth: {}
endpoints:
  - path: "/rest/user/1"
    method: "GET"
    params: {}
    headers: {}
    body: {}
    source: "config"
```

Optional bearer auth:

```yaml
auth:
  type: "bearer"
  token: "YOUR_TOKEN"
```

## Usage

Run one research pass:

```bash
python scripts/run_agent.py
```

Outputs are written to:

- `endpoints/`
- `resources/`
- `hypotheses/`
- `experiments/` for all executed mutations and their outcomes
- `findings/` only for `Confirmed` results
- `index.md`

Local memory and state are stored in:

- `raw/memory_store.json`
- `raw/agent_state.json`

If the local state files are missing, empty, or invalid JSON, the program recreates them automatically instead of crashing.

## Limitations

This is an early-stage research utility, not a mature scanner.

- It only tests configured HTTP endpoints.
- It only reasons about IDOR-style object identifier changes.
- It does not discover auth context on its own.
- It does not validate exploitability beyond response-based heuristics.
- Network restrictions in the runtime environment can make results inconclusive.
- Existing vault contents are not automatically archived between runs.

## Roadmap

Planned next steps for later versions:

- cleaner reset and archival workflow for generated notes
- better schema-aware identifier extraction
- stronger evidence thresholds for confirmed findings
- support for replaying authenticated sessions from local input
- richer markdown summaries for findings and experiments
- optional endpoint import from captured traffic

## Status

This repository now contains an early v1 implementation pass and should be treated as a deterministic local research utility, not as a complete autonomous security platform.
