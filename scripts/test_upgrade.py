"""Install revision 0 from a real HTTP Extensions index, then upgrade to revision 1."""

import argparse
import asyncio
import functools
import http.server
import json
import os
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path

from check_reports import run_check
from publication import digest, prepare_repository, verify_download
from test_integration import ROOT, check_session, free_port, initialize_client_runtime, wait_file
from platforms import process_options, resolve


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def previous_fixture(package, destination):
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as target:
        record = json.loads(source.read("provenance.json"))
        current_version = record["extension_version"]
        if record.get("channel") == "preview":
            if record["preview_revision"] > 1:
                record["preview_revision"] -= 1
            else:
                parts = list(map(int, record["version"].split(".")))
                if parts[2] < 1:
                    raise ValueError("First-preview upgrade fixture requires a previous patch version")
                parts[2] -= 1
                record["version"] = ".".join(map(str, parts))
        elif record["integration_revision"] < 1:
            raise ValueError("Upgrade fixture needs integration_revision >= 1")
        else:
            record["integration_revision"] -= 1
        from publication import extension_version
        record["extension_version"] = extension_version(record)
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "provenance.json":
                content = json.dumps(record).encode()
            elif item.filename == "blender_manifest.toml":
                content = content.replace(current_version.encode(), record["extension_version"].encode())
            target.writestr(item, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    package_hash = digest(args.package)
    run = ROOT / "build/tests" / f"upgrade-{time.time_ns()}"
    web = run / "http"
    web.mkdir(parents=True)
    old = web / "previous-integration.zip"
    previous_fixture(args.package, old)
    package = web / args.package.name
    shutil.copyfile(args.package, package)
    initialize_client_runtime(package, run / "client")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(web)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    old_record = prepare_repository(args.blender, old, web / "repository", f"{base}/{old.name}", allow_local_http=True)
    new_record = prepare_repository(args.blender, package, web / "candidate", f"{base}/{package.name}", current=old_record, allow_local_http=True)
    with (web / "candidate/index.json").open(encoding="utf-8") as stream:
        item = json.load(stream)["data"][0]
    assert item["platforms"] == [resolve()[0]] and item["blender_version_max"] == new_record["blender_max"]
    # Exercise readback failure as an actual HTTP transfer, not a mocked response.
    try:
        verify_download(f"{base}/{package.name}", "0" * 64, new_record["size"], allow_local_http=True)
    except ValueError:
        pass
    else:
        raise AssertionError("Altered published checksum was accepted")
    control = run / "control"
    control.mkdir()
    (control / "expected-upgrade.json").write_text(json.dumps({"before": old_record["extension_version"], "after": new_record["extension_version"]}))
    environment = os.environ.copy()
    environment["BLENDER_USER_RESOURCES"] = str(run / "profile")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    log = (run / "blender.log").open("w", encoding="utf-8")
    process = subprocess.Popen([
        str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1", "--python",
        str(ROOT / "tests/blender_integration_host.py"), "--", str(package), str(control),
        str(free_port()), str(free_port()), f"{base}/repository/index.json",
    ], env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        **process_options())
    try:
        wait_file(control / "service.json", process, timeout=90)
        connection = json.loads((control / "service.json").read_text())
        asyncio.run(check_session(connection))
        for name in ("index.json", "publication.json"):
            shutil.copyfile(web / "candidate" / name, web / "repository" / name)
        (control / "action.json").write_text(json.dumps({"action": "upgrade"}), encoding="utf-8")
        wait_file(control / "action-result.json", process, timeout=90)
        assert json.loads((control / "action-result.json").read_text())["status"] == "Passed"
        after = json.loads((control / "service.json").read_text())
        assert after["pid"] != connection["pid"]
        details = asyncio.run(check_session(after))
        (control / "stop").touch()
        process.wait(timeout=15)
        assert process.returncode == 0
        if digest(args.package) != package_hash:
            raise RuntimeError("Package changed during upgrade validation")
        report = {"status": "Passed", "package_sha256": package_hash, "index_install": "Passed", "revision_upgrade": f"{old_record['extension_version']} → {new_record['extension_version']}",
                  "preferences_and_credential_preserved": "Passed", "old_process_stopped": "Passed",
                  "published_archive_readback": "Passed", "checksum_mismatch_rejected": "Passed",
                  "details": details, "log": str(run / "blender.log")}
        (ROOT / "build/upgrade-tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        (control / "stop").touch()
        if process.poll() is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        log.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    run_check("upgrade", main)
