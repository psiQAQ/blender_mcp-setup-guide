"""Exercise Blender's real ZIP installer with controlled Windows child handles."""

import argparse
import ctypes
import hashlib
import json
import os
import runpy
import sys
import threading
import time
import traceback
import zipfile
from pathlib import Path


PACKAGE_ID = "rename_regression_fixture"
ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_CASES = {"destination_appears", "source_disappears", "other_error",
                  "destination_during_wait", "source_during_wait"}
WAIT_CASES = {"destination_during_wait", "source_during_wait", "cancel_during_wait"}


def create_package(path, version="1.0.0"):
    manifest = (
        'schema_version = "1.0.0"\n'
        f'id = "{PACKAGE_ID}"\n'
        f'version = "{version}"\n'
        'name = "Rename regression fixture"\n'
        'tagline = "Exercise native directory installation"\n'
        'maintainer = "Local regression test"\n'
        'type = "add-on"\n'
        'blender_version_min = "5.1.0"\n'
        'license = ["SPDX:GPL-3.0-or-later"]\n'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("blender_manifest.toml", manifest)
        archive.writestr("__init__.py", "def register():\n    pass\n\ndef unregister():\n    pass\n")
        archive.writestr("child/fixture.txt", "controlled reader fixture\n")
    return manifest


class ChildHandle:
    """Own only the handle opened by this test, allowing all three share flags."""

    def __init__(self, path):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        self.kernel.CreateFileW.restype = ctypes.c_void_p
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.kernel.CloseHandle.restype = ctypes.c_int
        self.handle = self.kernel.CreateFileW(str(path), 0x80000000, 7, None, 3, 0x02000000, None)
        if self.handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self.lock = threading.Lock()
        self.close_error = None
        self.closed_at = None

    def close(self):
        with self.lock:
            if self.handle is not None:
                if not self.kernel.CloseHandle(self.handle):
                    self.close_error = str(ctypes.WinError(ctypes.get_last_error()))
                else:
                    self.closed_at = time.monotonic()
                self.handle = None


def run_case(module, work, version, mode, name):
    case = work / name
    case.mkdir()
    repository = case / "repository"
    repository.mkdir()
    archive = case / "fixture.zip"
    is_reinstall = name.startswith("reinstall")
    manifest = create_package(archive, "1.0.1" if is_reinstall else "1.0.0")
    destination = repository / PACKAGE_ID
    staging = repository / (PACKAGE_ID + "@")
    messages = []
    transition = None
    transition_result = {"status": "Not Run"}
    native_rename = os.rename
    recovered_source = case / "moved-staging"

    def change_during_wait():
        try:
            if name == "destination_during_wait":
                destination.mkdir()
                (destination / "sentinel.txt").write_text("preserve concurrent destination", encoding="utf-8")
            elif name == "cancel_during_wait":
                module["signal_handler_sigint"](2, None)
            else:
                native_rename(staging, recovered_source)
            transition_result["status"] = "Passed"
        except Exception:
            transition_result.update(status="Failed", error=traceback.format_exc())

    def log(kind, value):
        nonlocal transition
        messages.append({"kind": kind, "message": value})
        is_retry = kind == "STATUS" and "Retrying directory rename" in value
        if is_retry and name in WAIT_CASES and transition is None:
            transition = threading.Timer(0.02, change_during_wait)
            transition.start()
        return name == "cancel_retry" and is_retry

    def install(package, logger):
        return module["subcmd_client"]._install_package_from_file_impl(
            logger, local_dir=str(repository), filepath_archive=str(package),
            blender_version_tuple=version, python_version_tuple=tuple(sys.version_info[:3]),
            manifest_compare=None, temp_prefix_and_suffix=(".regression-", ".old"),
        )

    result = {"name": name, "status": "Failed", "messages": messages, "rename_attempts": [],
              "evidence_kind": "injected boundary error" if name in BOUNDARY_CASES else "native filesystem"}
    if name in WAIT_CASES:
        result["transition_during_wait"] = transition_result
    if name == "cancel_during_wait":
        result["evidence_kind"] = "native handle plus cancellation-handler invocation"
    if is_reinstall:
        baseline = case / "baseline.zip"
        baseline_manifest = create_package(baseline)
        baseline_messages = []
        baseline_logger = module["MessageLogger"](
            lambda kind, value: baseline_messages.append({"kind": kind, "message": value}) or False)
        result["baseline_return"] = install(baseline, baseline_logger)
        result["baseline_messages"] = baseline_messages
        baseline_path = destination / "blender_manifest.toml"
        result["baseline_manifest_matches"] = baseline_path.is_file() and baseline_path.read_text(encoding="utf-8") == baseline_manifest
        if result["baseline_return"] is not True or not result["baseline_manifest_matches"]:
            result["failures"] = ["Initial installation for reinstall did not succeed"]
            return result

    held = None
    release = None
    first_failure_at = None

    def observe(source, target, *args, **kwargs):
        nonlocal held, release, first_failure_at
        if Path(source) != staging or Path(target) != destination:
            return native_rename(source, target, *args, **kwargs)
        first = not result["rename_attempts"]
        record = {"native": True}
        result["rename_attempts"].append(record)
        if first and (name.startswith(("file_", "directory_", "reinstall_")) or
                      name in {"cancel_retry", "cancel_during_wait"}):
            child = staging / "child"
            if name.startswith(("file_", "reinstall_")):
                child /= "fixture.txt"
            held = ChildHandle(child)
            result["controlled_handle"] = {"path": str(child), "desired_access": 0x80000000,
                                           "share_mask": 7, "owner_pid": os.getpid()}
        try:
            if first and name in BOUNDARY_CASES:
                record["native"] = False
                if name == "destination_appears":
                    destination.mkdir()
                    (destination / "sentinel.txt").write_text("preserve concurrent destination", encoding="utf-8")
                elif name == "source_disappears":
                    native_rename(staging, recovered_source)
                raise ctypes.WinError(32 if name == "other_error" else 5)
            native_rename(source, target, *args, **kwargs)
            record["status"] = "Passed"
        except OSError as error:
            record.update(status="Failed", winerror=error.winerror, error=str(error))
            if first:
                first_failure_at = time.monotonic()
                if name.endswith("_release") and held is not None:
                    release = threading.Timer(0.02, held.close)
                    release.start()
            raise

    started = time.monotonic()
    os.rename = observe
    try:
        result["installer_return"] = install(archive, module["MessageLogger"](log))
    except Exception:
        result["unexpected_exception"] = traceback.format_exc()
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 6)
        result["controlled_handle_open_at_installer_return"] = held is not None and held.closed_at is None
        if name == "cancel_during_wait":
            result["request_exit_at_installer_return"] = module["signal_handler_sigint"].__globals__["REQUEST_EXIT"]
        os.rename = native_rename
        if release is not None:
            release.join()
        if transition is not None:
            transition.join()
        if name == "cancel_during_wait":
            module["signal_handler_sigint"].__globals__["REQUEST_EXIT"] = False
        if held is not None:
            held.close()
            result["controlled_handle"]["close_error"] = held.close_error
            if first_failure_at is not None and held.closed_at is not None:
                result["controlled_handle"]["released_after_failure_seconds"] = round(
                    held.closed_at - first_failure_at, 6)

    installed_manifest = destination / "blender_manifest.toml"
    result["installed"] = installed_manifest.is_file()
    result["manifest_matches"] = result["installed"] and installed_manifest.read_text(encoding="utf-8") == manifest
    if is_reinstall:
        result["previous_version_present_after_attempt"] = result["installed"] and installed_manifest.read_text(encoding="utf-8") == baseline_manifest
        result["reinstall_scope"] = "Existing installer removes the old version before rename; rollback is outside this regression"
    result["staging_exists"] = staging.exists()
    result["staging_cleanup_after_handle_release_required"] = result["staging_exists"]
    result["rename_attempt_count"] = len(result["rename_attempts"])
    result["native_failure_count"] = sum(
        record["native"] and record.get("status") == "Failed" for record in result["rename_attempts"])
    result["first_failure_count"] = int(bool(result["rename_attempts"]) and
                                        result["rename_attempts"][0].get("status") == "Failed")
    retry_messages = [message for message in messages
                      if message["kind"] == "STATUS" and "Retrying directory rename" in message["message"]]
    result["retry_status_count"] = len(retry_messages)
    successful = name in {"clean", "reinstall"} or (mode == "patched" and name.endswith("_release"))
    result["expected_installer_return"] = successful
    failures = []
    if result.get("installer_return") is not successful:
        failures.append("Installer return did not match expected result")
    if result["installed"] is not successful or result["manifest_matches"] is not successful:
        failures.append("Installed manifest did not match expected result")
    held_through_cleanup = result["controlled_handle_open_at_installer_return"] and not successful
    if result["staging_exists"] and not held_through_cleanup:
        failures.append("Installer left staging directory behind")
    if result.get("unexpected_exception"):
        failures.append("Installer raised an unexpected exception")
    if held is not None and held.close_error:
        failures.append("Controlled handle could not be closed")
    if name in {"clean", "reinstall"}:
        if result["rename_attempt_count"] != 1 or result["native_failure_count"]:
            failures.append("Uncontended installation needed more than one rename")
    else:
        first_record = result["rename_attempts"][0] if result["rename_attempts"] else {}
        expected_error = 32 if name == "other_error" else 5
        if first_record.get("winerror") != expected_error:
            failures.append(f"First rename did not report WinError {expected_error}")
        if held is not None and not first_record.get("native"):
            failures.append("Controlled handle did not produce a real native failure")
        if mode == "patched" and name.endswith("_persistent"):
            if result["rename_attempt_count"] != 6 or not retry_messages:
                failures.append("Persistent refusal did not exhaust five bounded retries")
            if not 1.4 <= result["elapsed_seconds"] < 10:
                failures.append("Persistent refusal did not have bounded retry duration")
        elif mode == "patched" and name.endswith("_release"):
            if not 2 <= result["rename_attempt_count"] <= 6 or not retry_messages:
                failures.append("Released handle was not recovered through visible bounded retries")
        elif result["rename_attempt_count"] != 1:
            failures.append("Boundary, cancellation, or original installer unexpectedly retried")
        if name == "cancel_retry" and mode == "patched" and not retry_messages:
            failures.append("Cancellation never reached the retry status callback")
        if name in {"destination_appears", "source_disappears", "other_error"} and retry_messages:
            failures.append("A guarded boundary condition announced a retry")
        if name in WAIT_CASES and mode == "patched":
            if transition_result["status"] != "Passed" or len(retry_messages) != 1:
                failures.append("Fixture transition did not complete during the first retry wait")
        if name == "cancel_during_wait" and mode == "patched" and not result["request_exit_at_installer_return"]:
            failures.append("Cancellation flag was not set before the installer returned")
        if not successful and name not in {"cancel_retry", "cancel_during_wait"} and not any(
                message["kind"] == "ERROR" and f"WinError {expected_error}" in message["message"]
                for message in messages):
            failures.append("Installer did not preserve the final Windows error in its error message")
    if is_reinstall and successful and not any(message["message"].startswith("Reinstalled ") for message in messages):
        failures.append("Reinstall status was not reported")
    if name == "destination_appears" or (name == "destination_during_wait" and mode == "patched"):
        sentinel = destination / "sentinel.txt"
        result["concurrent_destination_preserved"] = sentinel.is_file() and sentinel.read_text(encoding="utf-8") == "preserve concurrent destination"
        if not result["concurrent_destination_preserved"]:
            failures.append("Concurrent destination was modified")
    if name == "source_disappears" or (name == "source_during_wait" and mode == "patched"):
        result["moved_source_preserved"] = (recovered_source / "blender_manifest.toml").is_file()
        if not result["moved_source_preserved"]:
            failures.append("Moved source was modified")
    result["failures"] = failures
    result["status"] = "Failed" if failures else "Passed"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--mode", choices=("original", "patched"), required=True)
    parser.add_argument("--version", choices=("5.2.2", "5.1.1"), required=True)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Native child-handle regression requires Windows")
    work = args.work.resolve()
    if not work.is_relative_to(ROOT / "build" / ".working"):
        parser.error("--work must be inside this repository's build/.working directory")
    work.mkdir(parents=True, exist_ok=True)
    module = runpy.run_path(str(args.installer.resolve()), run_name="native_rename_installer")
    report = {"status": "Not Run", "mode": args.mode, "installer": str(args.installer.resolve()),
              "installer_sha256": hashlib.sha256(args.installer.read_bytes()).hexdigest(),
              "blender_version": args.version, "python_version": sys.version,
              "scope": "real installer function and minimal fixture; no Blender GUI or MCP add-on execution",
              "cases": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for name in ("clean", "reinstall", "file_release", "directory_release", "file_persistent",
                 "directory_persistent", "destination_appears", "source_disappears", "other_error", "cancel_retry",
                 "destination_during_wait", "source_during_wait", "reinstall_release", "reinstall_persistent",
                 "cancel_during_wait"):
        result = run_case(module, work, tuple(map(int, args.version.split("."))), args.mode, name)
        report["cases"].append(result)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: {result['status']}", flush=True)
    report["status"] = "Passed" if all(case["status"] == "Passed" for case in report["cases"]) else "Failed"
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "Passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
