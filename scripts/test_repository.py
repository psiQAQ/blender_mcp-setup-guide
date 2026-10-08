"""Install this platform from a complete local or published Extensions index."""

import argparse
import asyncio
import functools
import http.server
import json
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from platforms import ROOT, process_options, resolve
from publication import digest, prepare_collection, verify_download
from test_integration import check_session, free_port, initialize_client_runtime, wait_file
from test_upgrade import QuietHandler, previous_fixture


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--public-index")
    return parser.parse_args(argv)


def select_package(index, platform, blender_version):
    """Accept an aggregate or channel index using Blender's exclusive maximum."""
    from pages_site import version_tuple
    items = [item for item in index["data"] if platform in item["platforms"]
             and version_tuple(item["blender_version_min"]) <= blender_version < version_tuple(item["blender_version_max"])]
    if len(items) != 1:
        raise ValueError("Index must select exactly one compatible platform package")
    return items[0]


def main(args):
    identifier, _ = resolve()
    packages = {path.name: next((path / "dist").glob("*.zip")) for path in args.artifacts.iterdir() if path.is_dir() and (path / "dist").exists()}
    package = packages[identifier]
    run = ROOT / "build/tests" / f"repository-{time.time_ns()}"
    run.mkdir(parents=True)
    initialize_client_runtime(package, run / "client")
    request = urllib.request.Request("https://github.com/psiQAQ/blender_mcp-setup-guide/releases", headers={"User-Agent": "BlenderMCPIntegrationCI"})
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200
        response.read(1)
    server = None
    if args.public_index:
        with urllib.request.urlopen(args.public_index, timeout=30) as response:
            index = json.load(response)
        probe = subprocess.check_output([str(args.blender), '--background', '--factory-startup', '--python-expr',
            "import bpy,json; print('HOST_VERSION='+json.dumps(list(bpy.app.version)))"], text=True)
        blender_version = tuple(json.loads(next(line.removeprefix('HOST_VERSION=') for line in probe.splitlines() if line.startswith('HOST_VERSION='))))
        item = select_package(index, identifier, blender_version)
        if (item['archive_hash'], item['archive_size']) != ('sha256:' + digest(package), package.stat().st_size):
            raise ValueError('Selected public package differs from the validated candidate')
        verify_download(item["archive_url"], digest(package), package.stat().st_size)
        url = args.public_index
    else:
        old = {}
        for key, path in packages.items():
            old[key] = run / f"previous-{key}.zip"
            previous_fixture(path, old[key])
        prepare_collection(args.blender, old, run / "repository")
        prepare_collection(args.blender, packages, run / "candidate")
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(run)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/repository/index.json"
    control = run / "control"
    control.mkdir()
    environment = {**os.environ, "BLENDER_USER_RESOURCES": str(run / "profile"), "PYTHONDONTWRITEBYTECODE": "1"}
    with (run / "blender.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1", "--python",
            str(ROOT / "tests/blender_integration_host.py"), "--", str(package), str(control), str(free_port()), str(free_port()), url],
            env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **process_options())
        try:
            wait_file(control / "service.json", process, timeout=90)
            connection = json.loads((control / "service.json").read_text())
            details = asyncio.run(check_session(connection))
            if not args.public_index:
                import shutil
                before = json.loads((run / "repository/publication.json").read_text())["extension_version"]
                after = json.loads((run / "candidate/publication.json").read_text())["extension_version"]
                from check_reports import write_json
                write_json(control / "expected-upgrade.json", {"before": before, "after": after})
                for path in (run / "candidate").iterdir():
                    shutil.copyfile(path, run / "repository" / path.name)
                write_json(control / "action.json", {"action": "upgrade"})
                wait_file(control / "action-result.json", process, timeout=90)
                assert json.loads((control / "action-result.json").read_text())["status"] == "Passed"
                details = asyncio.run(check_session(json.loads((control / "service.json").read_text())))
            (control / "stop").touch()
            process.wait(timeout=15)
            assert process.returncode == 0
            report = {"status": "Passed", "platform": identifier, "package_sha256": digest(package), "index_platform_selection": "Passed", "https_download_certificate_verification": "Passed", "certificate_source": "package-private certifi", "details": details, "log": str(run / "blender.log")}
            if args.public_index:
                report.update(publication_run_id=os.environ.get("GITHUB_RUN_ID"), integration_commit=os.environ.get("GITHUB_SHA"))
            name = "published" if args.public_index else "repository"
            (ROOT / "build" / f"{name}-tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, indent=2))
        finally:
            (control / "stop").touch()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            if server:
                server.shutdown()
                server.server_close()


def run(argv=None):
    from check_reports import run_check
    args = parse_arguments(argv)
    return run_check("published" if args.public_index else "repository", lambda: main(args))


if __name__ == "__main__":
    run()
