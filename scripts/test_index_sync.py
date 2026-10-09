"""Sync the unified index and detect an update from a verified published package."""

import argparse
import functools
import http.server
import json
import os
import subprocess
import sys
import threading
import tomllib
import zipfile
from pathlib import Path


def host(url, destination, previous_url=None, expected_version=None):
    import bpy
    import bl_pkg
    from bl_pkg import repo_stats_calc_outdated_for_repo_directory
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
    from native_install_capture import capture_install

    bpy.context.preferences.system.use_online_access = True
    repo = bpy.context.preferences.extensions.repos.new(
        name="Unified index validation", module="unified_test", remote_url=previous_url or url)
    repo.use_sync_on_startup = False
    position = list(bpy.context.preferences.extensions.repos).index(repo)
    baseline = None
    if previous_url:
        assert bpy.ops.extensions.repo_sync(repo_index=position) == {"FINISHED"}
        control = Path(os.environ['BLENDER_USER_CONFIG']).parents[1]
        with capture_install(control):
            assert bpy.ops.extensions.package_install(repo_index=position, pkg_id="blender_mcp_integration",
                                                      enable_on_install=False) == {"FINISHED"}
        manifest = Path(repo.directory) / "blender_mcp_integration/blender_manifest.toml"
        baseline = tomllib.loads(manifest.read_text(encoding="utf-8"))["version"]
        repo.remote_url = url
    assert bpy.ops.extensions.repo_sync(repo_index=position) == {"FINISHED"}
    cached = Path(repo.directory) / ".blender_ext/index.json"
    index = json.loads(cached.read_bytes())
    sys.path.insert(0, str(Path(bpy.utils.system_resource("SCRIPTS")) / "addons_core/bl_pkg/cli"))
    import blender_ext
    manifests = [blender_ext.pkg_manifest_from_dict_and_validate(item, from_repo=True, strict=False)
                 for item in index["data"]]
    assert all(not isinstance(item, str) for item in manifests), manifests
    assert blender_ext.pkg_manifest_detect_duplicates([(manifest, "", []) for manifest in manifests]) is None
    errors = []
    selected = [item for item in index["data"] if not blender_ext.repository_filter_skip(item,
        filter_blender_version=bpy.app.version, filter_platform="windows-x64",
        filter_python_version=sys.version_info[:3], skip_message_fn=None, error_fn=errors.append)]
    assert not errors, errors
    assert len(selected) == 1, selected
    assert selected[0]["blender_version_min"] == f"{bpy.app.version[0]}.{bpy.app.version[1]}.0"
    if expected_version:
        assert selected[0]["version"] == expected_version, selected[0]
    updates = repo_stats_calc_outdated_for_repo_directory(bl_pkg.repo_cache_store_ensure(), repo.directory)
    if baseline:
        assert baseline != selected[0]["version"], "The public index still contains the old version"
        assert updates == 1, f"Official Blender client detected {updates} updates instead of one"
    destination.write_text(json.dumps({"status": "Passed", "blender": bpy.app.version_string,
        "index_url": url, "entries": len(index["data"]), "selected": selected[0],
        "official_manifest_validation": "Passed", "official_duplicate_detection": "Passed",
        "actual_repository_sync": "Passed", "previous_version": baseline,
        "official_update_count": updates, "update_discovery": "Passed" if baseline else "Not Run"},
        indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--index-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-package", type=Path, help="Actual published ZIP matching the locked upgrade baseline")
    parser.add_argument("--expected-version", help="Reject a stale public version")
    args = parser.parse_args()
    from build_cache import task_directory
    from check_reports import preserve_failure, write_json
    from publication import digest, prepare_repository
    args.output.parent.mkdir(parents=True, exist_ok=True)
    preserve_failure(args.output.stem, args.output)
    with task_directory(args.output.stem) as run:
        write_json(args.output, {"status": "Not Run", "index_url": args.index_url})
        server = None
        baseline = None
        expected = None
        try:
            previous_url = ""
            if args.previous_package:
                with zipfile.ZipFile(args.previous_package) as archive:
                    source = json.loads(archive.read("provenance.json"))
                records = json.loads((Path(__file__).resolve().parents[1] / "packaging/upgrade-baselines.json").read_text(encoding="utf-8"))
                baseline = next(record for record in records.values()
                                if record["extension_version"] == source["extension_version"])
                expected = baseline["packages"][source["platform"]]
                assert args.previous_package.stat().st_size == expected["size"]
                assert digest(args.previous_package) == expected["sha256"], "Published baseline SHA-256 mismatch"
                web = run / "http"
                prepare_repository(args.blender, args.previous_package, web)
                class Handler(http.server.SimpleHTTPRequestHandler):
                    def log_message(self, *unused):
                        pass
                server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
                threading.Thread(target=server.serve_forever, daemon=True).start()
                previous_url = f"http://127.0.0.1:{server.server_port}/index.json"
            env = {**os.environ, "BLENDER_USER_RESOURCES": str(run / "profile"),
                   "BLENDER_USER_CONFIG": str(run / "profile/config"), "PYTHONDONTWRITEBYTECODE": "1"}
            with (run / "blender.log").open("w", encoding="utf-8") as log:
                subprocess.run([str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1",
                    "--python", str(Path(__file__).resolve()), "--", args.index_url, str(args.output.resolve()),
                    previous_url, args.expected_version or ""], env=env, stdout=log, stderr=subprocess.STDOUT,
                    check=True, timeout=180)
            report = json.loads(args.output.read_text(encoding="utf-8"))
            if baseline:
                report["baseline"] = {"version": baseline["extension_version"], **expected}
                write_json(args.output, report)
        except Exception as error:
            report = {"status": "Failed", "index_url": args.index_url,
                      "error": f"{type(error).__name__}: {error}", "update_discovery": "Not Run"}
            if baseline and expected:
                report['baseline'] = {"version": baseline['extension_version'], **expected}
            if (run / 'native-install.json').exists():
                trace = json.loads((run / 'native-install.json').read_bytes())
                report['native_install'] = trace
                errors = [str(message) for kind, message in trace['messages'] if kind == 'ERROR']
                if errors:
                    report['error'] = 'Native extension installation failed: ' + '; '.join(errors)
            write_json(args.output, report)
            raise
        finally:
            if server:
                server.shutdown()
                server.server_close()
    print(args.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    if "--" in sys.argv:
        url, destination, previous_url, expected_version = sys.argv[sys.argv.index("--") + 1:]
        host(url, Path(destination), previous_url or None, expected_version or None)
    else:
        main()
