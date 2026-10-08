"""Keep failed checks from leaving reusable Passed reports in a local build directory."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_check(name, operation):
    path = ROOT / "build" / f"{name}-tests.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": "Not Run", "reason": "Check in progress"}) + "\n", encoding="utf-8")
    try:
        return operation()
    except Exception as error:
        path.write_text(json.dumps({"status": "Failed", "error": f"{type(error).__name__}: {error}"}, indent=2) + "\n", encoding="utf-8")
        raise
