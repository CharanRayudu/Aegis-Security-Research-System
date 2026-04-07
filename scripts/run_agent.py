"""Entrypoint for the autonomous security research system."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.core.loop import AutonomousResearchLoop


def main() -> int:
    loop = AutonomousResearchLoop(str(REPO_ROOT / "config.yaml"))
    results = loop.run()
    print(f"[runner] Completed single-pass run across {len(results)} endpoint(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"[runner] Startup error: missing required file: {exc.filename}")
        raise SystemExit(1)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"[runner] Startup error: invalid config or local state file: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        print(f"[runner] Runtime error: {exc}")
        raise SystemExit(1)
