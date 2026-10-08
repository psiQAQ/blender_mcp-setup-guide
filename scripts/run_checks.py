"""Run repository tests using a project-local temporary directory."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


from build_cache import LATEST, cached_task, current_work

ROOT = Path(__file__).resolve().parents[1]


@cached_task("unit")
def main():
    temporary = current_work("unit")
    temporary.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(temporary)
    sys.dont_write_bytecode = True
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    report = {
        "status": "Passed" if result.wasSuccessful() else "Failed",
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped),
    }
    (LATEST / "unit-tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
