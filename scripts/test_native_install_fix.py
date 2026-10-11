"""Validate a native installer against real Windows handles and isolated Blender."""

import argparse
import json
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json
from publication import digest
from platforms import process_options


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--version", choices=("5.1.1", "5.2.2"), required=True)
    parser.add_argument("--runs", type=int, default=8)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("runs must be positive")
    args.blender = args.blender.resolve(strict=True)
    args.installer = args.installer.resolve(strict=True)
    args.package = args.package.resolve(strict=True)
    version_dir = ".".join(args.version.split(".")[:2])
    python = args.blender.parent / version_dir / "python/bin/python.exe"
    python_version = subprocess.check_output([
        str(python), "-I", "-S", "-B", "-c", "import platform; print(platform.python_version())",
    ], text=True).strip()
    work = current_work("native-install-fix")
    path = LATEST / f"native-install-fix-{args.label}-tests.json"
    report = {
        "status": "Not Run", "installer": str(args.installer), "installer_sha256": digest(args.installer),
        "package_sha256": digest(args.package), "blender_version": args.version,
        "python_version": python_version, "regression": {}, "installs": [], "blender_host": "Not Run",
        "system_deployment": "Not Run",
    }
    write_json(path, report)
    regression_dir = work / "regression"
    regression_dir.mkdir()
    regression_output = regression_dir / "result.json"
    with (regression_dir / "blender.log").open("w", encoding="utf-8") as log:
        regression = subprocess.run([
            str(python), "-I", "-S", "-B", str(ROOT / "tests/native_rename_regression.py"),
            "--installer", str(args.installer), "--output", str(regression_output),
            "--work", str(regression_dir), "--mode", "patched", "--version", args.version,
        ], stdout=log, stderr=subprocess.STDOUT, timeout=60)
    if regression_output.exists():
        report["regression"] = json.loads(regression_output.read_text(encoding="utf-8"))
    write_json(path, report)
    if regression.returncode:
        raise RuntimeError(f"Rename regression failed; see {regression_dir / 'blender.log'}")

    with zipfile.ZipFile(args.package) as archive:
        manifest_bytes = archive.read("blender_manifest.toml")
        package_id = tomllib.loads(manifest_bytes.decode())["id"]
    for number in range(1, args.runs + 1):
        case = work / f"install-{number}"
        repository = case / "extensions"
        repository.mkdir(parents=True)
        log_path = case / "blender.log"
        with log_path.open("w", encoding="utf-8") as log:
            outcome = subprocess.run([
                str(python), "-I", "-S", "-B", str(args.installer), "install-files", str(args.package),
                "--local-dir", str(repository), "--blender-version", args.version, "--python-version", python_version,
            ], stdout=log, stderr=subprocess.STDOUT, timeout=90)
        messages = log_path.read_text(encoding="utf-8").splitlines()
        errors = [line for line in messages if line.startswith(("ERROR", "FATAL_ERROR"))]
        retries = [line for line in messages if "Retrying directory rename" in line]
        manifest = repository / package_id / "blender_manifest.toml"
        matches = manifest.is_file() and manifest.read_bytes() == manifest_bytes
        passed = outcome.returncode == 0 and matches and not errors
        item = {
            "case": number, "status": "Passed" if passed else "Failed", "exit_code": outcome.returncode,
            "manifest_matches_package": matches, "first_rename_status": "Failed" if retries else ("Passed" if passed else "Unknown"),
            "retry_messages": retries, "errors": errors, "log": str(log_path),
        }
        report["installs"].append(item)
        write_json(path, report)
        print(f"native install {number}: {item['status']}; retries={len(retries)}", flush=True)
        if not passed:
            raise RuntimeError(f"Native install failed; see {log_path}")

    host_dir = work / "host"
    host_dir.mkdir()
    with (host_dir / "blender.log").open("w", encoding="utf-8") as log:
        host = subprocess.run([
            str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1",
            "--python", str(ROOT / "tests/blender_native_install_fix.py"), "--",
            str(args.package), str(args.installer), str(host_dir),
        ], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=log, stderr=subprocess.STDOUT, timeout=180, **process_options())
    host_result = host_dir / "host-result.json"
    if host_result.exists():
        report["blender_host"] = json.loads(host_result.read_text(encoding="utf-8"))
    write_json(path, report)
    if host.returncode or not isinstance(report["blender_host"], dict) or report["blender_host"]["status"] != "Passed":
        raise RuntimeError(f"Blender install/enable check failed; see {host_dir / 'blender.log'}")
    if digest(args.installer) != report["installer_sha256"] or digest(args.package) != report["package_sha256"]:
        raise RuntimeError("Installer or package changed during validation")
    if report["blender_host"].get("installer_selection") == "system":
        report["system_deployment"] = "Passed"
    report["status"] = "Passed"
    write_json(path, report)
    print(f"Blender {args.version}: native installation, enable and reinstall Passed", flush=True)


if __name__ == "__main__":
    label = sys.argv[sys.argv.index("--label") + 1]
    run_check(f"native-install-fix-{label}", main)
