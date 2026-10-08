"""Generate, build, validate and install two templates in isolated Blender."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from scaffold_extension import scaffold
from check_reports import run_check


from build_cache import LATEST, current_work

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    args = parser.parse_args()
    run = current_work("template")
    packages = []
    for identifier in ("template_alpha", "template_beta"):
        source = run / identifier
        scaffold(identifier, source)
        subprocess.run([sys.executable, "-B", str(source / "scripts/validate_extension.py"), "--source-path", str(source), "--skip-blender-validate"], check=True)
        subprocess.run([str(args.blender), "--command", "extension", "build", "--source-dir", str(source), "--output-dir", str(run)], check=True)
        package = run / f"{identifier}-1.0.0.zip"
        subprocess.run([str(args.blender), "--command", "extension", "validate", str(package)], check=True)
        packages.append(str(package))
    environment = os.environ.copy()
    environment["BLENDER_USER_RESOURCES"] = str(run / "profile")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1", "--python",
                             str(ROOT / "tests/blender_template_smoke.py"), "--", *packages],
                            env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
    (run / "blender.log").write_text(result.stdout, encoding="utf-8")
    line = next(line for line in result.stdout.splitlines() if line.startswith("TEMPLATE_RESULT="))
    report = json.loads(line.partition("=")[2])
    report["log"] = str(run / "blender.log")
    (LATEST / "template-tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run_check("template", main)
