# Aegis Security Research System

Local-first v1 of an Obsidian-compatible security research workflow focused on one concrete task: IDOR and broken object-level authorization testing for HTTP endpoints.

## What It Does

For each configured endpoint, the system:

1. Loads the target from `config.yaml`
2. Sends a baseline HTTP request
3. Generates a small IDOR-focused hypothesis set
4. Mutates path or query identifiers
5. Executes modified requests
6. Compares baseline vs mutated responses
7. Classifies the result as:
   - `Confirmed`
   - `Not Confirmed`
   - `Inconclusive`
8. Writes markdown notes into the Obsidian vault folders
9. Stores local JSON memory of what was tested

## Scope

This v1 intentionally supports only:

- HTTP-based testing
- IDOR / broken object-level authorization
- JSON or text responses
- Local file-based memory

It does not try to support browsers, XSS, SQLi, scheduling, multi-agent orchestration, or distributed execution.

## Repository Layout

```text
agent/
  core/loop.py
  llm/reasoner.py
  executor/http_client.py
  executor/mutation_engine.py
  validator/diff_engine.py
  storage/markdown_writer.py
  memory/store.py
scripts/run_agent.py
config.yaml
requirements.txt
endpoints/
resources/
hypotheses/
experiments/
findings/
raw/
notes/
index.md
```

## Configuration

Edit `config.yaml`:

```yaml
base_url: "https://example.com"
headers:
  Accept: "application/json"
auth: {}
endpoints:
  - path: "/rest/user/1"
    method: "GET"
    params: {}
    headers: {}
    body: {}
    source: "config"
```

Optional bearer authentication:

```yaml
auth:
  type: "bearer"
  token: "YOUR_TOKEN"
```

## Run

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the agent:

```bash
python scripts/run_agent.py
```

## Output

The system writes Obsidian-friendly markdown into:

- `endpoints/`
- `resources/`
- `hypotheses/`
- `experiments/`
- `findings/`
- `index.md`

It also stores local state in `raw/` while running.
