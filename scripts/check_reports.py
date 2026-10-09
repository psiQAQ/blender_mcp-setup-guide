"""Keep failed checks from leaving reusable Passed reports in a local build directory."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from build_cache import LATEST, task_directory, existing_work, mark


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    """Publish complete test messages to readers in another process."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.pending")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def preserve_failure(name, path):
    """Keep the observed failure and its diagnostics before another attempt starts."""
    if not path.exists():
        return
    raw = path.read_bytes()
    report = json.loads(raw)
    if report.get("status") != "Failed":
        return
    destination = LATEST / "evidence/failed-checks" / name / hashlib.sha256(raw).hexdigest()[:16]
    if destination.exists():
        return
    source = LATEST / "evidence" / name
    destination.mkdir(parents=True)
    if source.exists():
        shutil.copytree(source, destination / "diagnostics")
    write_json(destination / "report.json", report)


def run_check(name, operation):
    path = LATEST / f"{name}-tests.json"
    if child_work := os.environ.get('BLENDER_MCP_CHECK_WORK'):
        with existing_work(child_work):
            try:
                return operation()
            except Exception as error:
                report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                report.pop('reason', None)
                report.update(status='Failed', error=f'{type(error).__name__}: {error}')
                write_json(path, report)
                raise
    path.parent.mkdir(parents=True, exist_ok=True)
    preserve_failure(name, path)
    path.write_text(json.dumps({"status": "Not Run", "reason": "Check in progress"}) + "\n", encoding="utf-8")
    mark(name, 'Not Run', reason='Check in progress')
    with task_directory(name) as work:
        try:
            if operation.__module__ == '__main__':
                # The child releases imported native SDK modules before parent cleanup.
                environment = {**os.environ, 'BLENDER_MCP_CHECK_WORK': str(work)}
                subprocess.run([sys.executable, '-B', str(Path(sys.argv[0]).resolve()), *sys.argv[1:]],
                               env=environment, check=True)
                result = None
            else:
                result = operation()
            report = json.loads(path.read_text(encoding='utf-8'))
            mark(name, report['status'], package_sha256=report.get('package_sha256'))
            return result
        except Exception as error:
            report = json.loads(path.read_text(encoding='utf-8'))
            if report.get('status') != 'Failed':
                write_json(path, {"status": "Failed", "error": f"{type(error).__name__}: {error}"})
            mark(name, 'Failed', error=str(error))
            raise
