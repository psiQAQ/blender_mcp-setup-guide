"""Bind successful reports to the exact package and native CI environment."""

import argparse
import json
from pathlib import Path

from platforms import ROOT, resolve
from publication import digest


def collect(package):
    identifier, _ = resolve()
    package_hash = digest(package)
    for name in ("unit", "template", "integration", "upgrade", "gui", "minimum"):
        path = ROOT / "build" / f"{name}-tests.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["status"] != "Passed":
            raise ValueError(f"Required validation did not pass: {name}")
        if name not in {"unit", "template"} and report.get("package_sha256") != package_hash:
            raise ValueError(f"Validation report refers to another ZIP: {name}")
        report.update(platform=identifier, package_sha256=package_hash)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    collect(parser.parse_args().package)
