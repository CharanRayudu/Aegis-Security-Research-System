"""Entrypoint for the autonomous security research system."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.core.loop import AutonomousResearchLoop


def main() -> int:
    config_path = REPO_ROOT / "config.yaml"
    loop = AutonomousResearchLoop(str(config_path))
    results = loop.run()
    print(f"[runner] Completed single-pass run across {len(results)} endpoint(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
