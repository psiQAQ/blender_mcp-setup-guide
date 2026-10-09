"""Compare independent native installer runs in disposable repository paths."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json
from publication import digest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--observe-recovery", action="store_true")
    parser.add_argument("--bounded-retry", action="store_true",
                        help="Test a guarded 1.55-second native rename retry; still report the first failure")
    parser.add_argument("--rename-delay", type=float, default=0, help="Diagnostic delay before the first native rename; no retry")
    parser.add_argument("--layout", choices=("plain", "node_modules", "venv"), default="plain",
                        help="Compare disposable installation paths with standard editor exclusion names")
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if args.runs < 1 or not 0 <= args.rename_delay <= 5:
        parser.error("runs must be positive and rename-delay must be between 0 and 5 seconds")
    if args.observe_recovery and args.bounded_retry:
        parser.error("choose one recovery diagnostic")
    python_version = subprocess.check_output([
        str(args.python), "-I", "-S", "-B", "-c", "import platform; print(platform.python_version())",
    ], text=True).strip()
    run = current_work("native-rename")
    report = {"status": "Not Run", "package_sha256": digest(args.package),
              "installer_sha256": digest(args.installer), "python": str(args.python), "python_version": python_version,
              "blender_version": args.version, "rename_delay": args.rename_delay, "layout": args.layout,
              "bounded_retry": args.bounded_retry, "cases": [],
              "instrumentation": "os.rename observation, accessible file handles and Restart Manager after failure",
              "production_installer_changes": "Not Run"}
    report_path = LATEST / f"native-rename-{args.label}-tests.json"
    for number in range(args.runs):
        parent = run if args.layout == "plain" else run / (".venv" if args.layout == "venv" else args.layout)
        case = parent / f"case-{number + 1}"
        target = case / "profile/extensions/integration_test"
        target.mkdir(parents=True)
        telemetry = case / "renames.json"
        with (case / "blender.log").open("w", encoding="utf-8") as log:
            outcome = subprocess.run([
                str(args.python), "-I", "-S", "-B", str(ROOT / "tests/native_install_probe.py"),
                str(args.installer), str(telemetry), "bounded-retry" if args.bounded_retry else ("observe-recovery" if args.observe_recovery else "observe"),
                "install-files", str(args.package.resolve()), "--local-dir", str(target),
                "--blender-version", args.version, "--python-version", python_version,
            ], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "BLENDER_MCP_PROBE_RENAME_DELAY": str(args.rename_delay)},
                stdout=log, stderr=subprocess.STDOUT, timeout=60)
        item = {"case": number + 1, "exit_code": outcome.returncode,
                "installed": (target / "blender_mcp_integration/blender_manifest.toml").is_file(),
                "log": str(case / "blender.log")}
        if telemetry.exists():
            item.update(json.loads(telemetry.read_text()))
        initial_failed = any(entry.get("status") == "Failed" for entry in item.get("renames", []))
        item["status"] = "Passed" if item["installed"] and outcome.returncode == 0 and not initial_failed else "Failed"
        if initial_failed and item["installed"]:
            item["diagnostic_recovery"] = "Passed"
        report["cases"].append(item)
        write_json(report_path, report)
        print(f"case {number + 1}: {item['status']}", flush=True)
    report["status"] = "Passed" if all(case["status"] == "Passed" for case in report["cases"]) else "Failed"
    write_json(report_path, report)
    if report["status"] == "Failed":
        raise SystemExit(1)


if __name__ == "__main__":
    label = sys.argv[sys.argv.index("--label") + 1]
    run_check(f"native-rename-{label}", main)
